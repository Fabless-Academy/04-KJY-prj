QT += core gui qml quick 3dcore 3drender 3dinput 3dextras
CONFIG += c++17
TARGET = TOPST_DashBoard
TEMPLATE = app

SOURCES += \
    main.cpp \
    tcpclient.cpp \
    laneribbonmesh.cpp \
    lanecorridormesh.cpp \
    appcontroller.cpp

HEADERS += \
    tcpclient.h \
    laneribbonmesh.h \
    lanecorridormesh.h \
    appcontroller.h

RESOURCES += \
    qml.qrc \
    icons.qrc
