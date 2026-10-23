#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QSurfaceFormat>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include "tcpclient.h"
#include "appcontroller.h"
#include "laneribbonmesh.h"
#include "lanecorridormesh.h"

int main(int argc, char *argv[]) {
    QGuiApplication app(argc, argv);
    app.setApplicationName(QStringLiteral("TOPST_DashBoard"));

    // Qt3D 장면이 OpenGLES 2.0 기준으로 동작하도록 기본 surface format을 맞춤
    QSurfaceFormat format;
    format.setRenderableType(QSurfaceFormat::OpenGLES);
    format.setVersion(2, 0);
    QSurfaceFormat::setDefaultFormat(format);

    // QML에서 직접 사용할 커스텀 lane mesh 타입을 등록
    qmlRegisterType<LaneRibbonMesh>("Zonal", 1, 0, "LaneRibbonMesh");
    qmlRegisterType<LaneCorridorMesh>("Zonal", 1, 0, "LaneCorridorMesh");

    // 기본 연결 대상은 localhost로 두고, config.json이 있으면 그 값으로 덮어씀
    QString ip = "127.0.0.1";
    int port = 5000;
    int controlPort = 10001;
    QFile configFile("config.json");
    if (configFile.open(QIODevice::ReadOnly)) {
        QJsonObject cfg = QJsonDocument::fromJson(configFile.readAll()).object();
        ip = cfg.value("server_ip").toString(ip);
        port = cfg.value("server_port").toInt(port);
        controlPort = cfg.value("control_port").toInt(controlPort);
        configFile.close();
    }

    TcpClient tcpClient;
    tcpClient.setControlEndpoint(ip, controlPort);
    AppController appController;

    // C++ 객체를 QML 전역 context에 올려 UI에서 바로 참조
    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("tcpClient", &tcpClient);
    engine.rootContext()->setContextProperty("app", &appController);
    engine.load(QUrl(QStringLiteral("qrc:/qml/main.qml")));

    if (engine.rootObjects().isEmpty())
        return -1;

    // 화면이 준비된 뒤 telemetry/result 서버에 접속을 시작
    tcpClient.connectTo(ip, port);
    return app.exec();
}
