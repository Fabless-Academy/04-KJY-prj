#ifndef TCPCLIENT_H
#define TCPCLIENT_H

#include <QByteArray>
#include <QDateTime>
#include <QObject>
#include <QString>
#include <QTcpSocket>

class QJsonObject;

class TcpClient : public QObject {
    Q_OBJECT

public:
    explicit TcpClient(QObject *parent = nullptr);

    // 메인 telemetry/result 스트림 연결과 시나리오 제어용 endpoint 설정 함수
    Q_INVOKABLE void connectTo(const QString &ip, int port);
    Q_INVOKABLE void setControlEndpoint(const QString &ip, int port);
    Q_INVOKABLE void selectScenario(const QString &name);
    void connectFromConfig();

signals:
    // 수신 JSON을 QML이 바로 쓰기 쉬운 단위 signal로 분해해 전달
    void telemetryUpdated(double rpm, double speedKmh, double fuelL, double steering);
    void speedRecommendationUpdated(double recommendedSpeedKmh, const QString &status, double closestObjectYRatio);
    void simulatedBrakeLedUpdated(bool active);
    void laneStatusUpdated(const QString &laneStatusJson);
    void laneDataUpdated(const QString &lanesJson, int frameWidth, int frameHeight);
    void laneModelUpdated(const QString &laneModelJson);
    void objectDataUpdated(const QString &objectsJson);
    void connectionStatusChanged(const QString &status);
    void endpointChanged(const QString &endpoint);
    void scenarioCatalogUpdated(const QString &currentName, const QString &scenarioListJson);

private:
    // 내부적으로는 newline-delimited JSON 스트림을 줄 단위로 분리해 처리
    void setConnectionStatus(const QString &status);
    void onReadyRead();
    void processLine(const QByteArray &line);
    void publishTelemetry(const QJsonObject &object);
    void publishSpeedRecommendation(const QJsonObject &object);
    void publishSimulatedBrakeLed(const QJsonObject &object);
    void publishScenarioCatalog(const QJsonObject &object);
    void publishLaneStatus(const QJsonObject &object, int frameWidth);
    void publishLaneData(const QJsonObject &object, int frameWidth);
    void publishLaneModel(const QJsonObject &object);
    void publishObjects(const QJsonObject &object);

    QTcpSocket socket_;
    QByteArray buffer_;
    QString connectionStatus_;
    QString endpoint_;
    QString controlHost_ = QStringLiteral("127.0.0.1");
    int controlPort_ = 10001;
    qint64 lastTelemetryReceivedMs_ = 0;
    double lastRpm_ = 0.0;
    double lastSpeedKmh_ = 0.0;
    double lastFuelLiters_ = 0.0;
    double lastSteering_ = 0.0;
};

#endif
