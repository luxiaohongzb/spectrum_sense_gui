import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt
from util import find_max
class CrosshairPlotWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.x0 = 2200
        self.x1 = 2400
        # 创建布局
        layout = QVBoxLayout()
        self.setLayout(layout)

        # 创建 LabelItem
        self.label = pg.LabelItem(justify='right')

        # 创建 GraphicsLayoutWidget
        self.win = pg.GraphicsLayoutWidget()
        # layout.addWidget(self.label)  # 将标签添加到布局中
        # self.win.setStyleSheet("background-color: white;")
        self.win.addItem(self.label)
        # self.win.setWindowTitle("频谱监控图")
        layout.addWidget(self.win)
        # 创建 PlotWidget
        self.p1 = self.win.addPlot(row=1, col=0)
        self.p2 = self.win.addPlot(row=2, col=0)
        self.p1.setLabel(axis='left',text='功率/dbm')
        self.p1.setLabel(axis='bottom',text='频率/MHz') 

        self.p2.setLabel(axis='left',text='功率/dbm')
        self.p2.setLabel(axis='bottom',text='频率/MHz') 
        self.win.setMinimumHeight(800)
        self.freq = []
        self.power = []
        # 添加 LinearRegionItem
        self.region = pg.LinearRegionItem()
        self.region.setZValue(10)
        self.p2.addItem(self.region, ignoreBounds=True)
        self.p1.enableAutoRange(axis='y')
        self.p2.enableAutoRange(axis='y')
        # 添加十字标尺
         # 禁用鼠标缩放功能
        self.p1.setMouseEnabled(x=True, y=False)
        self.p2.setMouseEnabled(x=True, y=False)
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.p1.addItem(self.vLine, ignoreBounds=True)
        self.p1.addItem(self.hLine, ignoreBounds=True)
        self.vLine.setPen(pg.mkPen('w', style=Qt.DashLine))  # 设置十字标尺为虚线
        self.hLine.setPen(pg.mkPen('w', style=Qt.DashLine))  # 设置十字标尺为虚线
              # 在底部添加标签
        self.bottomLabel = pg.LabelItem(justify='center')
        self.win.addItem(self.bottomLabel, row=3, col=0)
        self.bottomLabel.setText("频谱监控图")
        # 监听鼠标移动事件
        self.p1.scene().sigMouseMoved.connect(self.mouseMoved)

        # 连接区域变化信号
        self.region.sigRegionChanged.connect(self.update)
        self.update()
        # data1 = 10000 + 15000 * pg.gaussianFilter(np.random.random(size=10000), 10) + 3000 * np.random.random(size=10000)
        # self.setData(data1)
    def set_range(self,x0,x1):
        self.x0 = x0
        self.x1 = x1
    def get_range(self):
        return self.x0 , self.x1

    def mouseMoved(self, evt):
        pos = evt
        if self.p1.sceneBoundingRect().contains(pos):
            mousePoint = self.p1.vb.mapSceneToView(pos)
            index = int(mousePoint.x())
            # if index > 0 and index < len(self.freq):
            self.label.setText("<span style='font-size: 12pt'>freq:%0.1f,   <span style='color: red'>power:%0.1f</span>" % (mousePoint.x(), mousePoint.y()))
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())

    def setData(self, freq,power):
        self.freq = freq
        self.power = power
    
        self.p1.plot(freq, power ,pen="g")
        self.p2d = self.p2.plot(freq,power, pen="w")
        self.region.setClipItem(self.p2d)
        self.region.setRegion([1000, 2000])

    def update(self):
        region = self.region.getRegion()
        minX, maxX = region
        self.p1.setXRange(minX, maxX, padding=0)
    def updatePlot(self, frequency, power):
        # self.p1.setXRange(self.get_range()[0],self.get_range()[1])
        if(len(frequency)==0 or len(power) ==  0):
            return 0,0
        # 清除之前的图形
        self.clearPlot()
        self.setData(frequency,power)
        max_x,max_y = find_max(frequency,power)
        # print("max freq value:"+str(max_y)+"db at "+str(max_x)+"MHz")
        return max_x,max_y
    def clearPlot(self):
    
        self.p1.clearPlots()
        self.p2.clearPlots()
 
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    mainWindow = CrosshairPlotWidget()
    mainWindow.show()

    data1 = 10000 + 15000 * pg.gaussianFilter(np.random.random(size=10000), 10) + 3000 * np.random.random(size=10000)
    data2 = 15000 + 15000 * pg.gaussianFilter(np.random.random(size=10000), 10) + 3000 * np.random.random(size=10000)
    mainWindow.setData(data1)

    sys.exit(app.exec_())
