# -*- coding: utf-8 -*-

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import os
import sys
import threading
import struct
import ctypes
import re
import math
import global_var as gl


from numpy import double
import ui_main
from gs_usb.gs_usb import GsUsb
from gs_usb.gs_usb_frame import GsUsbFrame
from gs_usb.constants import (
    CAN_EFF_FLAG,
    CAN_ERR_FLAG,
    CAN_RTR_FLAG,
    CAN_EFF_MASK,
)

time_Start = 0
class MainDlg(QDialog, ui_main.Ui_dlgMain):
  __USBCAN = None
  __DevTypeList = {"DEV_USBCAN"  : 3,
                   "DEV_USBCAN2" : 4 }
  __devType = None
  __Chn     = None
  __timer   = None
  __baud    = '''
            Time0    Time1
10 Kbps      0x9F     0xFF
20 Kbps      0x18     0x1C
40 Kbps      0x87     0xFF
50 Kbps      0x09     0x1C
80 Kbps      0x83     0xFF
100 Kbps     0x04     0x1C
125 Kbps     0x03     0x1C
200 Kbps     0x81     0xFA
250 Kbps     0x01     0x1C
400 Kbps     0x80     0xFA
500 Kbps     0x00     0x1C
666 Kbps     0x80     0xB6
800 Kbps     0x00     0x16
1000 Kbps    0x00     0x14
'''
  
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  def __init__(self, parent=None):
    super(MainDlg, self).__init__(parent)
    self.setupUi(self)

    self.cmb_Chn.addItem("0")
    self.cmb_Chn.addItem("1")
    self.cmb_Chn.setCurrentIndex(0)

    self.lineEdit_AccCode.setText("00000000")
    self.lineEdit_AccMask.setText("FFFFFFFF")
    self.cmb_NomBitSet.addItem("10Kbps")
    self.cmb_NomBitSet.addItem("20Kbps")
    self.cmb_NomBitSet.addItem("50Kbps")
    self.cmb_NomBitSet.addItem("100Kbps")
    self.cmb_NomBitSet.addItem("125Kbps")
    self.cmb_NomBitSet.addItem("250Kbps")
    self.cmb_NomBitSet.addItem("500Kbps")
    self.cmb_NomBitSet.addItem("800Kbps")
    self.cmb_NomBitSet.addItem("1Mbps")
    self.cmb_NomBitSet.setCurrentIndex(0)
    
    self.cmb_DataBitSet.addItem("10Kbps")
    self.cmb_DataBitSet.addItem("20Kbps")
    self.cmb_DataBitSet.addItem("50Kbps")
    self.cmb_DataBitSet.addItem("100Kbps")
    self.cmb_DataBitSet.addItem("125Kbps")
    self.cmb_DataBitSet.addItem("250Kbps")
    self.cmb_DataBitSet.addItem("500Kbps")
    self.cmb_DataBitSet.addItem("800Kbps")
    self.cmb_DataBitSet.addItem("1Mbps")
    self.cmb_DataBitSet.setCurrentIndex(0)

    self.cmb_Filter.addItem(u"接收全部类型")
    self.cmb_Filter.addItem(u"只接收标准帧")
    self.cmb_Filter.addItem(u"只接收扩展帧")
    self.cmb_Filter.setCurrentIndex(0)

    self.cmb_Mode.addItem(u"正常")
    self.cmb_Mode.addItem(u"只听")
    self.cmb_Mode.addItem(u"自测")
    self.cmb_Mode.setCurrentIndex(0)

    self.cmb_FrameType.addItem(u"标准帧")
    self.cmb_FrameType.addItem(u"扩展帧")
    self.cmb_FrameType.setCurrentIndex(0)

    self.cmb_FrameFormat.addItem(u"数据帧")
    self.cmb_FrameFormat.addItem(u"远程帧")
    self.cmb_FrameFormat.setCurrentIndex(0)

    self.pushBtn_startCAN.setDisabled(1)
    self.pushBtn_txdata.setDisabled(1)
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  #自动关联的槽函数
  @pyqtSlot()
  def on_pushBtn_connect_clicked(self):
    if self.pushBtn_connect.text() == u'连接':
      devs = GsUsb.scan()
      if len(devs) == 0:
          self.cmb_devType.clear()
          QMessageBox.information(self, u"错误",  u"找不到设备")
          err = -1
      else:
        self.cmb_devType.addItem("CANned Pi")
        self.cmb_devType.setCurrentIndex(0)
        self.__USBCAN=devs[0]
        self.pushBtn_startCAN.setDisabled(0) 
        self.cmb_NomBitSet.setDisabled(0)
        self.cmb_DataBitSet.setDisabled(0)
        self.pushBtn_connect.setText(u'关闭')

    elif self.pushBtn_connect.text() == u'关闭':
      if time_Start == 1:
        self.__timer.cancel()
      self.__USBCAN.stop()
      self.cmb_devType.setDisabled(0)
      self.cmb_Chn.setDisabled(0)
      self.cmb_NomBitSet.setDisabled(0)
      self.cmb_DataBitSet.setDisabled(0)
      self.pushBtn_startCAN.setDisabled(1)
      self.pushBtn_txdata.setDisabled(1)
      self.pushBtn_connect.setText(u'连接')

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  @pyqtSlot()
  def on_pushBtn_startCAN_clicked(self):
    self.__Chn = self.cmb_Chn.currentIndex()
    gl.change_global_var(self.__Chn)
    qs = self.lineEdit_AccCode.text()
    if len(qs)%2 != 0:
      qs = qs.zfill(len(qs)+1)
    AccCode =bytes.fromhex(qs).hex()
    qs = self.lineEdit_AccMask.text()
    if len(qs)%2 != 0:
      qs = qs.zfill(len(qs)+1)
    AccMask =bytes.fromhex(qs).hex()
    qs = self.cmb_NomBitSet.currentText();      nomBitRateSet    = qs;
    qs = self.cmb_DataBitSet.currentText();     dataBitRateSet   = qs;

    # qs = self.DataBitRate_Set.currentIndex();  DataBitRate   = qs;
    filter = self.cmb_Filter.currentIndex() + 1
    mode   = self.cmb_Mode.currentIndex()
    if nomBitRateSet == "10Kbps":
      nomBitRate = 10000
    elif nomBitRateSet == "20Kbps":
      nomBitRate = 20000
    elif nomBitRateSet == "50Kbps":
      nomBitRate = 50000
    elif nomBitRateSet == "100Kbps":
      nomBitRate = 100000
    elif nomBitRateSet == "125Kbps":
      nomBitRate = 125000
    elif nomBitRateSet == "250Kbps":
      nomBitRate = 250000   
    elif nomBitRateSet == "500Kbps":
      nomBitRate = 500000    
    elif nomBitRateSet == "800Kbps":
      nomBitRate = 800000         
    elif nomBitRateSet == "1Mbps":
      nomBitRate = 1000000      
    else:
      return False     
    if dataBitRateSet == "10Kbps":
      dataBitRate = 10000
    elif dataBitRateSet == "20Kbps":
      dataBitRate = 20000
    elif dataBitRateSet == "50Kbps":
      dataBitRate = 50000
    elif dataBitRateSet == "100Kbps":
      dataBitRate = 100000
    elif dataBitRateSet == "125Kbps":
      dataBitRate = 125000
    elif dataBitRateSet == "250Kbps":
      dataBitRate = 250000   
    elif dataBitRateSet == "500Kbps":
      dataBitRate = 500000    
    elif dataBitRateSet == "800Kbps":
      dataBitRate = 800000         
    elif dataBitRateSet == "1Mbps":
      dataBitRate = 1000000      
    else:
      return False
    if not self.__USBCAN.set_bitrate(self.__Chn,nomBitRate):
      QMessageBox.information(self, u"错误",  u"Can not set bitrate for gs_usb")
      err = 0
      return
    else:
      err = 1
    if err == 1:
      self.pushBtn_txdata.setDisabled(0)
      self.__USBCAN.start()     
      self.__timer = threading.Timer(0.1, self.can_rx)
      self.__timer.start()
      time_Start == 1
    elif err == 0:
      QMessageBox.information(self, u"错误",  u"初始化失败")
    elif err == -1:
      QMessageBox.information(self, u"错误",  u"设备不存在")

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  @pyqtSlot(str)
  def on_lineEdit_AccCode_textChanged(self, s):
    if self.pushBtn_connect.text() == u'关闭':
      self.on_pushBtn_startCAN_clicked()
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  @pyqtSlot(str)
  def on_lineEdit_AccMask_textChanged(self, s):
    if self.pushBtn_connect.text() == u'关闭':
      self.on_pushBtn_startCAN_clicked()
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  @pyqtSlot(int)
  def on_NomBitRate_Set_currentIndexChanged(self, i):
    if self.pushBtn_connect.text() == u'关闭':
      self.on_pushBtn_startCAN_clicked()

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  @pyqtSlot(int)
  def on_DataBitRate_Set_currentIndexChanged(self, i):
    if self.pushBtn_connect.text() == u'关闭':
      self.on_pushBtn_startCAN_clicked()

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  @pyqtSlot(int)
  def on_cmb_Filter_currentIndexChanged(self, i):
    if self.pushBtn_connect.text() == u'关闭':
      self.on_pushBtn_startCAN_clicked()
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  @pyqtSlot(int)
  def on_cmb_Mode_currentIndexChanged(self, i):
    if self.pushBtn_connect.text() == u'关闭':
      self.on_pushBtn_startCAN_clicked()

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  @pyqtSlot()
  def on_pushBtn_txdata_clicked(self):
    frameType   = self.cmb_FrameType.currentIndex()
    frameFormat = self.cmb_FrameFormat.currentIndex()
    qs = self.lineEdit_ID.text()
    if len(qs)%2 != 0:
      qs = qs.zfill(len(qs)+1)
    ID = bytearray.fromhex(qs)
    ID = list(ID)
    lens =len(ID)
    canid = 0
    for i in range(lens): 
      canid = canid + ID[i]*pow(256,(lens-1-i))
    data = self.lineEdit_Data.text()
    data = bytearray.fromhex(data)
    data = bytes(data)
    frame = GsUsbFrame(can_id=canid, channel=self.__Chn, data=data)
    if self.__USBCAN.send(frame):
        pass
        print("TX  {}".format(frame))

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  @pyqtSlot()
  def on_pushBtn_baudHelp_clicked(self):
    self.textEdit_recv.insertPlainText(self.__baud)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  @pyqtSlot()
  def on_pushBtn_clr_clicked(self):
    self.textEdit_recv.clear()
    
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  def can_rx(self):
    iframe  = GsUsbFrame()
    if self.__USBCAN.read(iframe, 1):
      self.textEdit_recv.insertPlainText(format(iframe) + '\r\n')
    self.__timer = threading.Timer(0.1, self.can_rx)
    self.__timer.start()
    time_Start == 1



#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

app = QApplication(sys.argv)
mainDlg = MainDlg()
mainDlg.show()
app.exec_()



