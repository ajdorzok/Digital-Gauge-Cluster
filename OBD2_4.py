import sys
import os
import time
import threading
from functools import partial
import math
import obd
from datetime import datetime
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QWidget, QApplication, QDialog
from PyQt5.QtGui import QBrush, QPen, QPainter, QPalette, QIcon
from PyQt5.QtCore import Qt, QThread

#Fonts
font = QtGui.QFont()
font.setFamily("Yu Gothic UI")
font.setPointSize(24)
font.setStyleStrategy(QtGui.QFont.PreferDefault)

small_font = QtGui.QFont()
small_font.setFamily("Yu Gothic UI")
small_font.setPointSize(12)
small_font.setStyleStrategy(QtGui.QFont.PreferDefault)

big_font = QtGui.QFont()
big_font.setFamily("Yu Gothic UI")
big_font.setPointSize(130)
big_font.setStyleStrategy(QtGui.QFont.PreferDefault)

directory = os.path.realpath(__file__).split(os.path.basename(__file__))
filepath = directory[0]

class OBDThread(QThread):
    signal = QtCore.pyqtSignal(float, float, float, float, float, int)
    temp, speed, rpm = 0.0, 0.0, 0.0
    maf, eqr = 1.0, 1.0 #initialize as 1 to avoid dividing by zero
    num_of_mafs = 1 #keeps track of how many MAF sensor readings have occured
                    #this is used for calculating the simple moving average for MPG

    def __init__(self):
        super(OBDThread, self).__init__()
        self.sleepinterval = 0.015

    def run(self):
        while threading.main_thread().is_alive():
            self.signal.emit(self.temp,self.speed,self.rpm,self.eqr, self.maf, self.num_of_mafs)
            time.sleep(self.sleepinterval)

    def setIntervalTime(self, sleeptime):
        self.sleepinterval = sleeptime

def new_temp(t):
    if mw.metric is False:
        t1 = t.value.to('degF')
        OBDThread.temp = t1.magnitude
    else:
        OBDThread.temp = t.value.magnitude

def new_speed(s):
    if mw.metric is False:
        s1 = s.value.to('mph')
        OBDThread.speed = s1.magnitude
    else:
        OBDThread.speed = s.value.magnitude

def new_rpm(r):
    OBDThread.rpm = r.value.magnitude

def new_maf(m):
    OBDThread.maf = m.value.magnitude
    OBDThread.num_of_mafs += 1

def new_eqr(e):
    OBDThread.eqr = e.value.magnitude

def OBD2_setup():
    connection.watch(obd.commands.SPEED, callback=new_speed) #km/h
    connection.watch(obd.commands.RPM, callback=new_rpm)
    connection.watch(obd.commands.MAF, callback=new_maf) #grams/sec
    connection.watch(obd.commands.COOLANT_TEMP, callback=new_temp) #degrees Celsius
    connection.watch(obd.commands.COMMANDED_EQUIV_RATIO, callback=new_eqr) #air/fuel ratio
    connection.start()

class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        app.focusChanged.connect(self.maintainFocus) #prevents a double clicking issue with the main buttons
        # Variables
        self.intervals = 0
        self.SMA = 0
        self.RPMlimit = 6.0
        self.radius = 190
        self.centerX = 408
        self.centerY = 270
        self.fuelsize = 20.0 #size of the fuel tank
        self.fuellevel = 20.0 #how much fuel is in the fuel tank
        self.metric = False
        self.colorindex = 1
        self.colorindex2 = 0
        self.colorindex3 = 0
        self.shadeindex = 1
        self.colors = {
            0: Qt.white,
            1: Qt.red,
            2: Qt.darkGreen,
            3: Qt.blue,
            4: Qt.cyan,
            5: Qt.magenta,
            6: Qt.yellow,
            7: Qt.black
        }
        self.shades = {
            0: Qt.white,
            1: Qt.lightGray,
            2: Qt.gray,
            3: Qt.darkGray,
            4: Qt.black
        }
        self.styleshades = {  # these rgb values match the Qt color presets
            0: "rgb(255,255,255)",
            1: "rgb(192,192,192)",
            2: "rgb(160,160,164)",
            3: "rgb(128,128,128)",
            4: "rgb(0,0,0)"
        }
        self.lockout = False #this is used to prevent multiple instances of the Settings menu
        self.lockout2 = False #this is used to prevent multiple instances of the Data Logger menu
        self.menus = [] #list of all open menus, used for hiding menus when returning to home screen
        self.labels = [] #list of labels, used for changing labels to white when background is black
        # Read Config File
        try:
            with open(filepath + "config.txt", "r") as reader:
                config = reader.read()
                config_values = [str(x) for x in config.split(" ")]
                self.metric = bool(float(config_values[0]))
                self.colorindex = int(float(config_values[1]))
                self.colorindex2 = int(float(config_values[2]))
                self.colorindex3 = int(float(config_values[3]))
                self.shadeindex = int(float(config_values[4]))
                self.fuelsize = float(config_values[5])
                self.RPMlimit = float(config_values[6])
                self.fuellevel = float(config_values[7])
        except:
            with open(filepath + "config.txt", "w") as writer:
                L = [str(float(self.metric)) + " ",
                     str(float(self.colorindex)) + " ",
                     str(float(self.colorindex2)) + " ",
                     str(float(self.colorindex3)) + " ",
                     str(float(self.shadeindex)) + " ",
                     str(float(self.fuelsize)) + " ",
                     str(float(self.RPMlimit)) + " ",
                     str(float(self.fuellevel))]
                writer.writelines(L)

        self.pen1 = QPen(self.colors[self.colorindex2], 3, Qt.DashLine, Qt.RoundCap)
        self.paletteSetUp()
        # Main window
        self.setObjectName("Home")
        self.resize(800, 480)
        self.setMaximumSize(QtCore.QSize(800, 480))
        self.setMinimumSize(QtCore.QSize(800, 480))
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        # Buttons
        self.Home_Button = QtWidgets.QPushButton(self)
        self.Home_Button.setGeometry(QtCore.QRect(0, 0, 96, 96))
        self.Home_Button.setCheckable(True)
        self.Home_Button.setObjectName("Home_Button")
        self.Home_Button.setIcon(QIcon(filepath + "homeicon.png"))
        self.Home_Button.setIconSize(self.Home_Button.rect().size()*0.9)
        self.Home_Button.setFont(small_font)
        self.Home_Button.setStyleSheet("background-color:{}; border:None".format(self.shades[self.shadeindex]))
        self.Home_Button.toggled.connect(self.returnHome)

        self.Data_Log_Button = QtWidgets.QPushButton(self)
        self.Data_Log_Button.setGeometry(QtCore.QRect(0, 192, 96, 96))
        self.Data_Log_Button.setCheckable(True)
        self.Data_Log_Button.setObjectName("pushButton4")
        self.Data_Log_Button.setIcon(QIcon(filepath + "datalogicon.png"))
        self.Data_Log_Button.setIconSize(self.Data_Log_Button.rect().size() * 0.9)
        self.Data_Log_Button.setFont(small_font)
        self.Data_Log_Button.setStyleSheet("background-color:{}; border:None".format(self.shades[self.shadeindex]))
        self.Data_Log_Button.toggled.connect(self.createDataLogMenu)

        self.Settings_Button = QtWidgets.QPushButton(self)
        self.Settings_Button.setGeometry(QtCore.QRect(0, 384, 96, 96))
        self.Settings_Button.setCheckable(True)
        self.Settings_Button.setObjectName("pushButton5")
        self.Settings_Button.setIcon(QIcon(filepath + "settingscog.png"))
        self.Settings_Button.setIconSize(self.Settings_Button.rect().size()*0.9)
        self.Settings_Button.setFont(small_font)
        self.Settings_Button.setStyleSheet("background-color:{}; border:None".format(self.shades[self.shadeindex]))
        self.Settings_Button.toggled.connect(self.createSettingsMenu)

        self.Main_Buttons = QtWidgets.QButtonGroup(self)
        self.Main_Buttons.addButton(self.Home_Button, 0)
        self.Main_Buttons.addButton(self.Data_Log_Button, 1)
        self.Main_Buttons.addButton(self.Settings_Button, 2)
        self.Main_Buttons.setExclusive(True)

        Fuel_Gauge_Reset_Button = QtWidgets.QPushButton(self)
        Fuel_Gauge_Reset_Button.setGeometry(QtCore.QRect(752, 49, 48, 431))
        Fuel_Gauge_Reset_Button.setStyleSheet("background-color: rgba(255, 255, 255, 0); border:None")
        Fuel_Gauge_Reset_Button.setObjectName("Fuel_Gauge_Reset_Button")
        Fuel_Gauge_Reset_Button.clicked.connect(self.resetFuelDialog)
        # Lines
        Vertical_line = QtWidgets.QFrame(self)
        Vertical_line.setGeometry(QtCore.QRect(86, 0, 20, 480))
        Vertical_line.setFrameShadow(QtWidgets.QFrame.Plain)
        Vertical_line.setFrameShape(QtWidgets.QFrame.VLine)
        Vertical_line.setObjectName("Vertical_line")

        Horizontal_line = QtWidgets.QFrame(self)
        Horizontal_line.setGeometry(QtCore.QRect(96, 47, 704, 3))
        Horizontal_line.setFrameShadow(QtWidgets.QFrame.Plain)
        Horizontal_line.setFrameShape(QtWidgets.QFrame.HLine)
        Horizontal_line.setObjectName("Horizontal_line")
        # Labels
        self.Header_Label = QtWidgets.QLabel(self)
        self.Header_Label.setGeometry(QtCore.QRect(96, 0, 210, 48))
        self.Header_Label.setFont(font)
        self.Header_Label.setAlignment(QtCore.Qt.AlignLeft)
        self.Header_Label.setObjectName("Header_Label")
        self.Header_Label.setText("Home")
        self.Header_Label.setPalette(self.mainPalette)
        self.labels.append(self.Header_Label)

        Tach_Label = QtWidgets.QLabel(self)
        Tach_Label.setGeometry(QtCore.QRect(385, 120, 110, 48))
        Tach_Label.setFont(font)
        Tach_Label.setAlignment(QtCore.Qt.AlignLeft)
        Tach_Label.setObjectName("Tach_Label")
        Tach_Label.setText("RPM")
        self.labels.append(Tach_Label)

        Tach_Sub_Label = QtWidgets.QLabel(self)
        Tach_Sub_Label.setGeometry(QtCore.QRect(395, 154, 110, 24))
        Tach_Sub_Label.setFont(small_font)
        Tach_Sub_Label.setAlignment(QtCore.Qt.AlignLeft)
        Tach_Sub_Label.setObjectName("Tach_Sub_Label")
        Tach_Sub_Label.setText("X 1000")
        self.labels.append(Tach_Sub_Label)

        self.tachSetup()

        Temp_Label = QtWidgets.QLabel(self)
        Temp_Label.setGeometry(QtCore.QRect(97, 48, 180, 24))
        Temp_Label.setFont(small_font)
        Temp_Label.setAlignment(QtCore.Qt.AlignLeft)
        Temp_Label.setObjectName("Temp_Label")
        Temp_Label.setText("Engine Coolant Temp:")
        self.labels.append(Temp_Label)

        Eqr_Label = QtWidgets.QLabel(self)
        Eqr_Label.setGeometry(QtCore.QRect(97, 415, 180, 24))
        Eqr_Label.setFont(small_font)
        Eqr_Label.setAlignment(QtCore.Qt.AlignLeft)
        Eqr_Label.setObjectName("Eqr_Label")
        Eqr_Label.setText("Air to Fuel Ratio:")
        self.labels.append(Eqr_Label)

        self.MPG_Label = QtWidgets.QLabel(self)
        self.MPG_Label.setGeometry(QtCore.QRect(570, 48, 180, 24))
        self.MPG_Label.setFont(small_font)
        self.MPG_Label.setAlignment(QtCore.Qt.AlignRight)
        self.MPG_Label.setObjectName("MPG_Label")
        if self.metric is False:
            self.MPG_Label.setText("Miles per Gallon:")
        else:
            self.MPG_Label.setText("Liters per 100 Km:")
        self.labels.append(self.MPG_Label)

        self.Range_Label = QtWidgets.QLabel(self)
        self.Range_Label.setGeometry(QtCore.QRect(570, 100, 180, 24))
        self.Range_Label.setFont(small_font)
        self.Range_Label.setAlignment(QtCore.Qt.AlignRight)
        self.Range_Label.setObjectName("Range_Label")
        if self.metric is False:
            self.Range_Label.setText("Miles till empty:")
        else:
            self.Range_Label.setText("Km till empty:")
        self.labels.append(self.Range_Label)

        self.Time_Label = QtWidgets.QLabel(self)
        self.Time_Label.setGeometry(QtCore.QRect(700, 0, 100, 48))
        self.Time_Label.setFont(font)
        self.Time_Label.setAlignment(QtCore.Qt.AlignCenter)
        self.Time_Label.setObjectName("Time_Label")
        self.labels.append(self.Time_Label)

        self.Speed_Label = QtWidgets.QLabel(self)
        self.Speed_Label.setGeometry(QtCore.QRect(423,263,328,215))
        self.Speed_Label.setFont(big_font)
        self.Speed_Label.setAlignment(QtCore.Qt.AlignCenter)
        self.Speed_Label.setObjectName("Speed_Label")
        self.labels.append(self.Speed_Label)

        self.Speed_Units_Label = QtWidgets.QLabel(self)
        self.Speed_Units_Label.setGeometry(QtCore.QRect(625,455,120,24))
        self.Speed_Units_Label.setFont(small_font)
        self.Speed_Units_Label.setAlignment(QtCore.Qt.AlignCenter)
        self.Speed_Units_Label.setObjectName("Speed_Units_Label")
        if self.metric is False:
            self.Speed_Units_Label.setText("Miles per Hour")
        else:
            self.Speed_Units_Label.setText("Km per Hour")
        self.labels.append(self.Speed_Units_Label)
        # 7-segment counters
        self.Temp_Display = QtWidgets.QLCDNumber(self)
        self.Temp_Display.setGeometry(QtCore.QRect(97, 68, 180, 36))
        self.Temp_Display.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.Temp_Display.setFrameShape(0)
        self.Temp_Display.setObjectName("Temp_Display")
        self.labels.append(self.Temp_Display)

        self.MPG_Display = QtWidgets.QLCDNumber(self)
        self.MPG_Display.setGeometry(QtCore.QRect(573, 68, 180, 36))
        self.MPG_Display.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.MPG_Display.setFrameShape(0)
        self.MPG_Display.setObjectName("MPG_Display")
        self.labels.append(self.MPG_Display)

        self.Eqr_Display = QtWidgets.QLCDNumber(self)
        self.Eqr_Display.setGeometry(QtCore.QRect(53, 440, 180, 36))
        self.Eqr_Display.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.Eqr_Display.setFrameShape(0)
        self.Eqr_Display.setObjectName("Eqr_Display")
        self.labels.append(self.Eqr_Display)

        self.Range_Display = QtWidgets.QLCDNumber(self)
        self.Range_Display.setGeometry(QtCore.QRect(573, 120, 180, 36))
        self.Range_Display.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.Range_Display.setFrameShape(0)
        self.Range_Display.setObjectName("Range_Display")
        self.labels.append(self.Range_Display)
        # Progress Bar
        self.Fuel_Guage = QtWidgets.QProgressBar(self)
        self.Fuel_Guage.setGeometry(QtCore.QRect(752, 49, 48, 431))
        self.Fuel_Guage.lower()
        self.Fuel_Guage.setValue(int(self.fuellevel/self.fuelsize*100))
        self.Fuel_Guage.setOrientation(QtCore.Qt.Vertical)
        self.Fuel_Guage.setObjectName("Fuel_Guage")
        # Scene
        self.Guage_Cluster = QtWidgets.QGraphicsScene(self)
        self.Guage_Cluster.setBackgroundBrush(QBrush(self.shades[self.shadeindex]))
        self.Guage_Cluster.setSceneRect(0,0,799,479)
        # Graphics View
        Gauge_Cluster_View = QtWidgets.QGraphicsView(self.Guage_Cluster,self)
        Gauge_Cluster_View.setGeometry(0,0,801,481)
        Gauge_Cluster_View.setFrameRect(QtCore.QRect(0,0,800,480))
        Gauge_Cluster_View.lower()
        Gauge_Cluster_View.setRenderHints(QPainter.Antialiasing)
        # Add scene items
        self.Tach_Ring = self.Guage_Cluster.addEllipse(208, 51, 425, 425, self.pen1, self.shades[self.shadeindex])
        self.Speed_Rect = self.Guage_Cluster.addRect(423, 263, 215, 215, Qt.transparent, self.shades[self.shadeindex])
        self.Tach_Pointer = self.Guage_Cluster.addRect(420, 228, 5, 245, self.colors[self.colorindex], self.colors[self.colorindex])
        self.Tach_Pointer.setTransformOriginPoint(423, 263)
        self.Tach_Pivot = self.Guage_Cluster.addEllipse(408, 247, 30, 30, self.colors[self.colorindex], Qt.black)

        if self.shadeindex == 4:
            self.mainPalette.setColor(QPalette.All, QPalette.Foreground, self.shades[0])
            self.Settings_Button.setIcon(QIcon(filepath + "settingscogI.png"))
            self.Data_Log_Button.setIcon(QIcon(filepath + "datalogiconI.png"))
            self.Home_Button.setIcon(QIcon(filepath + "homeiconI.png"))
            for label in self.labels:
                label.setPalette(self.mainPalette)
        # Threads
        self.th = OBDThread()
        self.th.signal.connect(self.displayUpdate)
        self.th.start()

    def displayUpdate(self, t, s, r, e, m, nom):
        currentTime = datetime.now()
        self.Time_Label.setText("{}:{}".format(currentTime.strftime("%I"), currentTime.strftime("%M")))
        self.Temp_Display.display(int(t))
        self.Speed_Label.setText(str(int(s)))
        if int(s) == 0:
            self.saveToConfig()
        self.Tach_Pointer.setRotation(r / (self.RPMlimit * 1000) * 270)
        self.Eqr_Display.display(e * 14.7)
        if nom != self.intervals:
            self.intervals = nom
            gps = ((m/14.7)/453.6)/6.701 #gallons per second
            mpg = s/(gps*3600) #instantaneous miles per gallon
            self.SMA = self.SMA + mpg
            if self.metric is True:
                try:
                    self.MPG_Display.display(235.215/self.SMA/nom)
                except:
                    self.MPG_Display.display(0)
                lps = gps * 3.78541 #liters per second
                self.fuellevel = self.fuellevel - lps
                self.Range_Display.display(int(self.SMA / nom * self.fuellevel))
            else:
                self.fuellevel = self.fuellevel - gps
                self.Range_Display.display(int(self.SMA/nom * self.fuellevel))
            self.Fuel_Guage.setValue(int(self.fuellevel / self.fuelsize * 100))

    def paletteSetUp(self):
        self.mainPalette = QPalette()
        self.mainPalette.setColor(QPalette.All, QPalette.Background, self.shades[self.shadeindex])

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            connection.stop()
            sys.exit(app.exec_())

    def resetFuelDialog(self):
        self.Dialog_Box = QDialog()
        self.Dialog_Box.setGeometry(200,120,400,240)
        self.Dialog_Box.setModal(True)
        self.Dialog_Box.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        # Labels
        self.Question_Label = QtWidgets.QLabel(self.Dialog_Box)
        self.Question_Label.setText("Are you sure you want to reset the fuel level?")
        self.Question_Label.setGeometry(0,60,400,24)
        self.Question_Label.setAlignment(QtCore.Qt.AlignCenter)
        self.Question_Label.setFont(small_font)
        # Buttons
        self.Accept_Button = QtWidgets.QPushButton(self.Dialog_Box)
        self.Accept_Button.setGeometry(100, 180,100,36)
        self.Accept_Button.setText("Accept")
        self.Accept_Button.setFont(small_font)
        self.Accept_Button.clicked.connect(self.resetFuelLevel)
        self.Accept_Button.clicked.connect(self.Dialog_Box.accept)

        self.Cancel_Button = QtWidgets.QPushButton(self.Dialog_Box)
        self.Cancel_Button.setDefault(True)
        self.Cancel_Button.setGeometry(200, 180,100,36)
        self.Cancel_Button.setText("Cancel")
        self.Cancel_Button.setFont(small_font)
        self.Cancel_Button.clicked.connect(self.Dialog_Box.reject)

        self.Dialog_Box.show()

    def resetFuelLevel(self):
        self.fuellevel = self.fuelsize

    def tachSetup(self):
        self.RPM_Labels = []
        palette = QPalette()
        palette.setColor(QPalette.All, QPalette.Foreground, self.colors[self.colorindex3])
        for i in range(0,int(2*self.RPMlimit)+1):
            if i%2 == 0:
                self.RPM_Labels.append(QtWidgets.QLabel(self))
                deg_angle = 90-((-270 * i) / (2 * self.RPMlimit))
                rad_angle = (math.pi * deg_angle) / 180
                self.RPM_Labels[int(i/2)].setGeometry(int((self.centerX-24)+(self.radius*math.cos(rad_angle))),
                                     int((self.centerY-24)+(self.radius*math.sin(rad_angle))),
                                     48, 48)
                self.RPM_Labels[int(i/2)].setFont(font)
                self.RPM_Labels[int(i / 2)].setPalette(palette)
                self.RPM_Labels[int(i/2)].setAlignment(QtCore.Qt.AlignRight)
                self.RPM_Labels[int(i/2)].setText(str(int(i/2)))
                self.RPM_Labels[int(i/2)].show()

    def tachDestroy(self):
        for labels in self.RPM_Labels:
            labels.hide()

    def returnHome(self):
        if self.Home_Button.isChecked() is True:
            self.Header_Label.setText("Home")
            for menu in self.menus:
                menu.hide()

    def saveToConfig(self):
        with open(filepath + "config.txt", "w") as writer:
            L = [str(float(self.metric)) + " ",
                 str(float(self.colorindex)) + " ",
                 str(float(self.colorindex2)) + " ",
                 str(float(self.colorindex3)) + " ",
                 str(float(self.shadeindex)) + " ",
                 str(float(self.fuelsize)) + " ",
                 str(float(self.RPMlimit)) + " ",
                 str(float(self.fuellevel))]
            writer.writelines(L)
        self.paletteSetUp()

    def createDataLogMenu(self):
        if self.Data_Log_Button.isChecked() is True:
            if self.lockout2 is False:
                self.dl = DataLogger()
                mw.Header_Label.setText("Data Logger")
                self.dl.setCursor(Qt.BlankCursor)
                self.menus.append(self.dl)
                self.dl.show()
                self.lockout2 = True
            else:
                self.dl.show()
                mw.Header_Label.setText("Data Logger")
        else:
            self.dl.hide()
            self.Header_Label.setText("Home")

    def maintainFocus(self):
        if self.Data_Log_Button.isChecked() is True:
            self.dl.raise_()
        if self.Settings_Button.isChecked() is True:
            self.sm.raise_()

    def createSettingsMenu(self):
        if self.Settings_Button.isChecked() is True:
            if self.lockout is False:
                self.sm = SettingsMenu()
                mw.Header_Label.setText("Settings")
                self.sm.setCursor(Qt.BlankCursor)
                self.menus.append(self.sm)
                self.sm.show()
                self.lockout = True
            else:
                self.sm.show()
                mw.Header_Label.setText("Settings")
        else:
            self.sm.hide()
            self.Header_Label.setText("Home")

class DataLogger(QWidget):
    def __init__(self):
        super().__init__()
        # Window Set Up
        self.setGeometry(97, 49, 702, 430)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setPalette(mw.mainPalette)
        self.setObjectName("Data Logger")
        # Variables
        self.datalogging = False
        self.firstlinewritten = False
        self.intervals = 0
        self.SMA = 0
        # Buttons
        self.Switch_Group = QtWidgets.QButtonGroup(self)
        self.Switch_Button = QtWidgets.QPushButton(self)
        self.Switch_Group.addButton(self.Switch_Button)
        self.Switch_Button.setGeometry(3, 2, 40, 40)
        self.Switch_Button.clicked.connect(self.switchLoggingState)
        # Labels
        self.Switch_Label = QtWidgets.QLabel(self)
        self.Switch_Label.setObjectName("Switch_Label")
        self.Switch_Label.setGeometry(QtCore.QRect(45, 10, 200, 24))
        self.Switch_Label.setFont(small_font)
        self.Switch_Label.setAlignment(QtCore.Qt.AlignLeft)
        self.Switch_Label.setText("Data Logging: Disabled")
        mw.labels.append(self.Switch_Label)
        # Text Edit Box
        self.Data_Text_Box = QtWidgets.QTextEdit(self)
        self.Data_Text_Box.setReadOnly(True)
        self.Data_Text_Box.setGeometry(3,45,698,380)


    def switchLoggingState(self):
        self.datalogging = not self.datalogging
        self.th = OBDThread()
        self.th.setIntervalTime(1.0)
        if self.datalogging is True:
            self.th.signal.connect(self.logData)
            self.th.start()
            self.Switch_Label.setText("Data Logging: Enabled")
            self.Switch_Button.setIcon(QIcon(filepath + "checkmark.png"))
            self.Switch_Button.setIconSize(self.Switch_Button.rect().size() * 0.9)
        else:
            self.th.quit()
            self.Switch_Label.setText("Data Logging: Disabled")
            self.Switch_Button.setIcon(QIcon(None))

    def logData(self, t, s, r, e, m, nom):
        if self.datalogging is True:
            gps = ((m/(e * 14.7))/453.6)/6.701 #gallons per second
            mpg = s/(gps*3600) #instantaneous miles per gallon
            if mw.metric is True:
                try:
                    mpg = 235.215/mpg #while at a stop the mpg is 0
                except:
                    mpg = 0
            with open("datalog.csv", "a") as writer:
                if self.firstlinewritten is False:
                    L =  "Temp,Speed,RPM,MPG, Fuel Level\n"
                    writer.write(L)
                    self.Data_Text_Box.append(L)
                    self.firstlinewritten = True
                L = "{},{},{},{},{}\n".format(t,s,r,mpg,mw.fuellevel)
                writer.write(L)
                self.Data_Text_Box.append(L)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            connection.stop()
            sys.exit(app.exec_())

class SettingsMenu(QWidget):
    def __init__(self):
        super().__init__()
        # Window Set Up
        self.setGeometry(97, 49, 702, 430)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setPalette(mw.mainPalette)
        self.setObjectName("Settings")
        # Radio Buttons
        unitsButtonGroup = QtWidgets.QButtonGroup(self)
        unitsButtonGroup.setExclusive(True)

        self.Metric_Button = QtWidgets.QPushButton(self)
        unitsButtonGroup.addButton(self.Metric_Button)
        self.Metric_Button.setCheckable(True)
        self.Metric_Button.setGeometry(3,3,40, 40)
        self.Metric_Button.setIconSize(self.Metric_Button.rect().size() * 0.9)
        if mw.metric is True:
            self.Metric_Button.toggle()
            self.Metric_Button.setIcon(QIcon(filepath + "checkmark.png"))
        else:
            self.Metric_Button.setIcon(QIcon(None))
        self.Metric_Button.toggled.connect(self.unitChange)

        self.Imperial_Button = QtWidgets.QPushButton(self)
        unitsButtonGroup.addButton(self.Imperial_Button)
        self.Imperial_Button.setCheckable(True)
        self.Imperial_Button.setGeometry(146, 3,40, 40)
        self.Imperial_Button.setIconSize(self.Imperial_Button.rect().size() * 0.9)
        if mw.metric is False:
            self.Imperial_Button.toggle()
            self.Imperial_Button.setIcon(QIcon(filepath + "checkmark.png"))
        else:
            self.Imperial_Button.setIcon(QIcon(None))
        self.Imperial_Button.toggled.connect(self.unitChange)
        # Labels
        self.Metric_Label = QtWidgets.QLabel(self)
        self.Metric_Label.setGeometry(43,12, 100, 24)
        self.Metric_Label.setFont(small_font)
        self.Metric_Label.setAlignment(QtCore.Qt.AlignLeft)
        self.Metric_Label.setText("Metric units")
        mw.labels.append(self.Metric_Label)

        self.Imperial_Label = QtWidgets.QLabel(self)
        self.Imperial_Label.setGeometry(186, 12, 100, 24)
        self.Imperial_Label.setFont(small_font)
        self.Imperial_Label.setAlignment(QtCore.Qt.AlignLeft)
        self.Imperial_Label.setText("Imperial units")
        mw.labels.append(self.Imperial_Label)

        self.Pointer_Color_Label = QtWidgets.QLabel(self)
        self.Pointer_Color_Label.setGeometry(3, 50, 220, 48)
        self.Pointer_Color_Label.setFont(font)
        self.Pointer_Color_Label.setAlignment(QtCore.Qt.AlignLeft)
        self.Pointer_Color_Label.setText("Pointer Color:")
        mw.labels.append(self.Pointer_Color_Label)

        self.Tach_Ring_Color_Label = QtWidgets.QLabel(self)
        self.Tach_Ring_Color_Label.setGeometry(3, 135, 240, 48)
        self.Tach_Ring_Color_Label.setFont(font)
        self.Tach_Ring_Color_Label.setAlignment(QtCore.Qt.AlignLeft)
        self.Tach_Ring_Color_Label.setText("Tach Ring Color:")
        mw.labels.append(self.Tach_Ring_Color_Label)

        self.Tach_Number_Color_Label = QtWidgets.QLabel(self)
        self.Tach_Number_Color_Label.setGeometry(3, 220, 300, 48)
        self.Tach_Number_Color_Label.setFont(font)
        self.Tach_Number_Color_Label.setAlignment(QtCore.Qt.AlignLeft)
        self.Tach_Number_Color_Label.setText("Tach Number Color:")
        mw.labels.append(self.Tach_Number_Color_Label)

        self.Background_Shade_Label = QtWidgets.QLabel(self)
        self.Background_Shade_Label.setGeometry(3, 305, 300, 48)
        self.Background_Shade_Label.setFont(font)
        self.Background_Shade_Label.setAlignment(QtCore.Qt.AlignLeft)
        self.Background_Shade_Label.setText("Background Shade:")
        mw.labels.append(self.Background_Shade_Label)

        self.RPM_Limit_Label = QtWidgets.QLabel(self)
        self.RPM_Limit_Label.setGeometry(int(self.width()/2)+3, 0, 220, 48)
        self.RPM_Limit_Label.setFont(font)
        self.RPM_Limit_Label.setAlignment(QtCore.Qt.AlignLeft)
        self.RPM_Limit_Label.setText("Set RPM Limit:")
        mw.labels.append(self.RPM_Limit_Label)

        self.RPM_Limit_Label2 = QtWidgets.QLabel(self)
        self.RPM_Limit_Label2.setGeometry(int(self.width()/2)+80, 55, 220, 24)
        self.RPM_Limit_Label2.setFont(small_font)
        self.RPM_Limit_Label2.setAlignment(QtCore.Qt.AlignLeft)
        self.RPM_Limit_Label2.setText("x 1,000 RPM")
        mw.labels.append(self.RPM_Limit_Label2)

        self.RPM_Button_Label = QtWidgets.QLabel(self)
        self.RPM_Button_Label.setGeometry(int(self.width()/2)+90, 98, 90, 24)
        self.RPM_Button_Label.setFont(small_font)
        self.RPM_Button_Label.setAlignment(QtCore.Qt.AlignLeft)
        self.RPM_Button_Label.setText(":500 RPM")
        mw.labels.append(self.RPM_Button_Label)

        self.Tank_Size_Label = QtWidgets.QLabel(self)
        self.Tank_Size_Label.setGeometry(int(self.width()/2)+3, 145, 240, 48)
        self.Tank_Size_Label.setFont(font)
        self.Tank_Size_Label.setAlignment(QtCore.Qt.AlignLeft)
        self.Tank_Size_Label.setText("Fuel Tank Size:")
        mw.labels.append(self.Tank_Size_Label)

        self.Tank_Size_Units_Label = QtWidgets.QLabel(self)
        self.Tank_Size_Units_Label.setGeometry(int(self.width()/2)+80, 195, 120, 24)
        self.Tank_Size_Units_Label.setFont(small_font)
        self.Tank_Size_Units_Label.setAlignment(QtCore.Qt.AlignLeft)
        if mw.metric is False:
            self.Tank_Size_Units_Label.setText("Gallons")
        else:
            self.Tank_Size_Units_Label.setText("Liters")
        mw.labels.append(self.Tank_Size_Units_Label)

        self.Tank_Size_Increment_Label = QtWidgets.QLabel(self)
        self.Tank_Size_Increment_Label.setGeometry(int(self.width()/2)+90, 240, 120, 24)
        self.Tank_Size_Increment_Label.setFont(small_font)
        self.Tank_Size_Increment_Label.setAlignment(QtCore.Qt.AlignLeft)
        if mw.metric is False:
            self.Tank_Size_Increment_Label.setText(": 1/2 Gallon")
        else:
            self.Tank_Size_Increment_Label.setText(": 1/2 Liter")
        mw.labels.append(self.Tank_Size_Increment_Label)
        #7 Segment Counters
        self.RPM_Limit_Display = QtWidgets.QLCDNumber(self)
        self.RPM_Limit_Display.setGeometry(QtCore.QRect(int(self.width()/2)+3, 50, 72, 36))
        self.RPM_Limit_Display.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.RPM_Limit_Display.setObjectName("RPM_Display")
        self.RPM_Limit_Display.display(mw.RPMlimit)
        mw.labels.append(self.RPM_Limit_Display)

        self.Tank_Size_Display = QtWidgets.QLCDNumber(self)
        self.Tank_Size_Display.setGeometry(QtCore.QRect(int(self.width()/2)+3, 190, 72, 36))
        self.Tank_Size_Display.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.Tank_Size_Display.setObjectName("RPM_Display")
        self.Tank_Size_Display.display(mw.fuelsize)
        mw.labels.append(self.Tank_Size_Display)
        #Buttons
        RPMadjustButtons = QtWidgets.QButtonGroup(self)
        RPMup = QtWidgets.QPushButton(self)
        RPMadjustButtons.addButton(RPMup, 0)
        RPMup.setGeometry(int(self.width()/2)+3, 90, 40, 40)
        RPMup.setFont(font)
        RPMup.setText("+")
        RPMup.clicked.connect(partial(self.changeRPMLimit, 0))

        RPMdown = QtWidgets.QPushButton(self)
        RPMadjustButtons.addButton(RPMdown, 1)
        RPMdown.setGeometry(int(self.width()/2)+45,90,40,40)
        RPMdown.setFont(font)
        RPMdown.setText("-")
        RPMdown.clicked.connect(partial(self.changeRPMLimit, 1))

        TankSizeadjustButtons = QtWidgets.QButtonGroup(self)
        TankUp = QtWidgets.QPushButton(self)
        TankSizeadjustButtons.addButton(TankUp, 0)
        TankUp.setGeometry(int(self.width()/2)+3, 230, 40, 40)
        TankUp.setFont(font)
        TankUp.setText("+")
        TankUp.clicked.connect(partial(self.changeTankSize, 0))

        TankDown = QtWidgets.QPushButton(self)
        TankSizeadjustButtons.addButton(TankDown, 1)
        TankDown.setGeometry(int(self.width()/2)+45, 230, 40, 40)
        TankDown.setFont(font)
        TankDown.setText("-")
        TankDown.clicked.connect(partial(self.changeTankSize, 1))

        savebuttons = QtWidgets.QButtonGroup(self)
        self.save = QtWidgets.QPushButton(self)
        savebuttons.addButton(self.save, 0)
        self.save.setGeometry(475, 365, 225, 60)
        self.save.setFont(font)
        self.save.setText("Save Settings")
        self.save.clicked.connect(mw.saveToConfig)
        # Lines
        Vertical_line = QtWidgets.QFrame(self)
        Vertical_line.setGeometry(QtCore.QRect(int(self.width()/2), 1, 1, self.height()))
        Vertical_line.setFrameShadow(QtWidgets.QFrame.Plain)
        Vertical_line.setFrameShape(QtWidgets.QFrame.VLine)
        Vertical_line.setObjectName("Vertical_line")
        # CheckBoxes
        self.colorbuttons = QtWidgets.QButtonGroup(self)
        self.colorbuttons2 = QtWidgets.QButtonGroup(self)
        self.colorbuttons3 = QtWidgets.QButtonGroup(self)
        self.shadebuttons = QtWidgets.QButtonGroup(self)
        colors = {
            0: "white",
            1: "red",
            2: "green",
            3: "blue",
            4: "cyan",
            5: "magenta",
            6: "yellow",
            7: "black"
        }
        self.shades = { #these rgb values match the Qt color presets
            0: "rgb(255,255,255)",
            1: "rgb(192,192,192)",
            2: "rgb(160,160,164)",
            3: "rgb(128,128,128)",
            4: "rgb(0,0,0)"
        }
        for i in range(8):
            self.button = QtWidgets.QPushButton(self)
            self.colorbuttons.addButton(self.button, i)
            self.colorbuttons.button(i).setGeometry(3 + (41 * i), 100, 40, 40)
            self.colorbuttons.button(i).setCheckable(True)
            self.colorbuttons.button(i).setAutoExclusive(True)
            self.colorbuttons.button(i).setStyleSheet("background-color:{}; border:None".format(colors[i]))
            self.colorbuttons.button(i).setObjectName(str(i))
            self.colorbuttons.button(i).setIconSize(self.colorbuttons.button(i).rect().size() * 0.9)
            self.colorbuttons.button(i).toggled.connect(partial(self.changePointerColor,
                                                                self.colorbuttons.button(i).objectName()))
            if i == mw.colorindex:
                self.colorbuttons.button(i).setChecked(True)

        for i in range(8):
            self.button = QtWidgets.QPushButton(self)
            self.colorbuttons2.addButton(self.button, i)
            self.colorbuttons2.button(i).setGeometry(3 + (41 * i), 185, 40, 40)
            self.colorbuttons2.button(i).setCheckable(True)
            self.colorbuttons2.button(i).setAutoExclusive(True)
            self.colorbuttons2.button(i).setStyleSheet("background-color:{}; border:None".format(colors[i]))
            self.colorbuttons2.button(i).setObjectName(str(i))
            self.colorbuttons2.button(i).setIconSize(self.colorbuttons2.button(i).rect().size() * 0.9)
            self.colorbuttons2.button(i).toggled.connect(partial(self.changeTachRingColor,
                                                                self.colorbuttons2.button(i).objectName()))
            if i == mw.colorindex2:
                self.colorbuttons2.button(i).setChecked(True)

        for i in range(8):
            self.button = QtWidgets.QPushButton(self)
            self.colorbuttons3.addButton(self.button, i)
            self.colorbuttons3.button(i).setGeometry(3 + (41 * i), 270, 40, 40)
            self.colorbuttons3.button(i).setCheckable(True)
            self.colorbuttons3.button(i).setAutoExclusive(True)
            self.colorbuttons3.button(i).setStyleSheet("background-color:{}; border:None".format(colors[i]))
            self.colorbuttons3.button(i).setObjectName(str(i))
            self.colorbuttons3.button(i).setIconSize(self.colorbuttons3.button(i).rect().size() * 0.9)
            self.colorbuttons3.button(i).toggled.connect(partial(self.changeTachNumberColor,
                                                                self.colorbuttons3.button(i).objectName()))
            if i == mw.colorindex3:
                self.colorbuttons3.button(i).setChecked(True)

        for i in range(5):
            self.button = QtWidgets.QPushButton(self)
            self.shadebuttons.addButton(self.button, i)
            self.shadebuttons.button(i).setGeometry(3 + (41 * i), 355, 40, 40)
            self.shadebuttons.button(i).setCheckable(True)
            self.shadebuttons.button(i).setAutoExclusive(True)
            self.shadebuttons.button(i).setStyleSheet("background-color:{}; border:None".format(self.shades[i]))
            self.shadebuttons.button(i).setObjectName(str(i))
            self.shadebuttons.button(i).setIconSize(self.shadebuttons.button(i).rect().size() * 0.9)
            self.shadebuttons.button(i).toggled.connect(partial(self.changeBackgroundColor,
                                                                 self.shadebuttons.button(i).objectName()))
            if i == mw.shadeindex:
                self.shadebuttons.button(i).setChecked(True)

    def changePointerColor(self, index):
        mw.colorindex = int(index)
        mw.Tach_Pointer.setBrush(mw.colors[mw.colorindex])
        mw.Tach_Pointer.setPen(mw.colors[mw.colorindex])
        mw.Tach_Pivot.setPen(mw.colors[mw.colorindex])
        for button in self.colorbuttons.buttons():
            if button.isChecked():
                button.setIcon(QIcon(filepath + "checkmark.png"))
            else:
                button.setIcon(QIcon(None))

    def changeTachRingColor(self, index):
        mw.colorindex2 = int(index)
        mw.pen1.setColor(mw.colors[mw.colorindex2])
        mw.Tach_Ring.setPen(mw.pen1)
        for button in self.colorbuttons2.buttons():
            if button.isChecked():
                button.setIcon(QIcon(filepath + "checkmark.png"))
            else:
                button.setIcon(QIcon(None))

    def changeTachNumberColor(self, index):
        mw.colorindex3 = int(index)
        mw.tachDestroy()
        mw.tachSetup()
        for button in self.colorbuttons3.buttons():
            if button.isChecked():
                button.setIcon(QIcon(filepath + "checkmark.png"))
            else:
                button.setIcon(QIcon(None))

    def changeBackgroundColor(self, index):
        mw.shadeindex = int(index)
        mw.mainPalette.setColor(QPalette.All, QPalette.Background, mw.shades[mw.shadeindex])
        if mw.shadeindex == 4:
             mw.mainPalette.setColor(QPalette.All, QPalette.Foreground, mw.shades[0])
             mw.Settings_Button.setIcon(QIcon(filepath + "settingscogI.png"))
             mw.Data_Log_Button.setIcon(QIcon(filepath + "datalogiconI.png"))
             mw.Home_Button.setIcon(QIcon(filepath + "homeiconI.png"))
        else:
             mw.mainPalette.setColor(QPalette.All, QPalette.Foreground, mw.shades[4])
             mw.Settings_Button.setIcon(QIcon(filepath + "settingscog.png"))
             mw.Data_Log_Button.setIcon(QIcon(filepath + "datalogicon.png"))
             mw.Home_Button.setIcon(QIcon(filepath + "homeicon.png"))
        mw.setPalette(mw.mainPalette)
        self.setPalette(mw.mainPalette)
        mw.Guage_Cluster.setBackgroundBrush(mw.shades[mw.shadeindex])
        mw.Speed_Rect.setBrush(mw.shades[mw.shadeindex])
        mw.Tach_Ring.setBrush(mw.shades[mw.shadeindex])
        mw.Home_Button.setStyleSheet("background-color:{}; border:None".format(self.shades[mw.shadeindex]))
        mw.Data_Log_Button.setStyleSheet("background-color:{}; border:None".format(self.shades[mw.shadeindex]))
        mw.Settings_Button.setStyleSheet("background-color:{}; border:None".format(self.shades[mw.shadeindex]))
        for label in mw.labels:
            label.setPalette(mw.mainPalette)
        if mw.lockout2 is True: #lockout2 will only be true if the data log menu has been created
            mw.dl.setPalette(mw.mainPalette)
        for button in self.shadebuttons.buttons():
            if button.isChecked():
                button.setIcon(QIcon(filepath + "checkmark.png"))
            else:
                button.setIcon(QIcon(None))

    def changeRPMLimit(self, index):
        if index == 0:
            mw.RPMlimit += 0.5
            self.RPM_Limit_Display.display(mw.RPMlimit)
            mw.tachDestroy()
            mw.tachSetup()

        if index == 1:
            mw.RPMlimit -= 0.5
            self.RPM_Limit_Display.display(mw.RPMlimit)
            mw.tachDestroy()
            mw.tachSetup()

    def changeTankSize(self, index):
        if index == 0:
            mw.fuelsize += 0.5
            self.Tank_Size_Display.display(mw.fuelsize)

        if index == 1:
            mw.fuelsize -= 0.5
            self.Tank_Size_Display.display(mw.fuelsize)

    def unitChange(self):
        if self.Metric_Button.isChecked():
            self.Metric_Button.setIcon(QIcon(filepath + "checkmark.png"))
            self.Imperial_Button.setIcon(QIcon(None))
            mw.metric = True
            mw.MPG_Label.setText("Liters per 100 Km:")
            mw.Speed_Units_Label.setText("Km per Hour")
            mw.Range_Label.setText("Km till empty")
            self.Tank_Size_Units_Label.setText("Liters")
            self.Tank_Size_Increment_Label.setText(": 1/2 Liter")
        if self.Imperial_Button.isChecked():
            self.Metric_Button.setIcon(QIcon(None))
            self.Imperial_Button.setIcon(QIcon(filepath + "checkmark.png"))
            mw.metric = False
            mw.MPG_Label.setText("Miles per Gallon:")
            mw.Speed_Units_Label.setText("Miles per Hour")
            mw.Range_Label.setText("Miles till empty")
            self.Tank_Size_Units_Label.setText("Gallons")
            self.Tank_Size_Increment_Label.setText(": 1/2 Gallon")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            connection.stop()
            sys.exit(app.exec_())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mw = MainWindow()
    connection = obd.Async(fast=True, check_voltage=False)
    OBD2_setup()
    mw.setCursor(Qt.BlankCursor)
    mw.showFullScreen()
    sys.exit(app.exec_())
