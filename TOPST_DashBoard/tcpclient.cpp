#include "tcpclient.h"

#include <QDebug>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QScopedPointer>

TcpClient::TcpClient(QObject *parent) : QObject(parent) {
    // 서버 연결 상태를 문자열 property로 유지해 QML에서 바로 표시
    connect(&socket_, &QTcpSocket::connected, this, [this]() {
        setConnectionStatus(QStringLiteral("Connected"));
        qDebug() << "Connected to telemetry server";
    });
    connect(&socket_, &QTcpSocket::disconnected, this, [this]() {
        setConnectionStatus(QStringLiteral("Disconnected"));
        qDebug() << "Disconnected from telemetry server";
    });
    connect(&socket_, &QTcpSocket::readyRead, this, &TcpClient::onReadyRead);
    connect(&socket_,
            QOverload<QAbstractSocket::SocketError>::of(&QTcpSocket::errorOccurred),
            this,
            [this](QAbstractSocket::SocketError) {
                setConnectionStatus(socket_.errorString());
                qWarning() << "Socket error:" << socket_.errorString();
            });
}

void TcpClient::connectTo(const QString &ip, int port) {
    // 현재 연결 대상을 사람이 읽기 쉬운 endpoint 문자열로도 저장
    endpoint_ = QStringLiteral("%1:%2").arg(ip).arg(port);
    emit endpointChanged(endpoint_);

    if (socket_.state() != QAbstractSocket::UnconnectedState) {
        // 기존 연결이 남아 있으면 강제로 끊고 새 연결을 시작
        socket_.abort();
    }

    setConnectionStatus(QStringLiteral("Connecting"));
    socket_.connectToHost(ip, quint16(port));
}

void TcpClient::setControlEndpoint(const QString &ip, int port) {
    controlHost_ = ip;
    controlPort_ = port;
}

void TcpClient::selectScenario(const QString &name) {
    if (name.trimmed().isEmpty()) {
        return;
    }

    // 시나리오 선택은 별도 control socket을 잠깐 열어 단발성 JSON 명령으로 보냄
    QScopedPointer<QTcpSocket> controlSocket(new QTcpSocket());
    controlSocket->connectToHost(controlHost_, quint16(controlPort_));
    if (!controlSocket->waitForConnected(1000)) {
        qWarning() << "Scenario control connect failed:" << controlSocket->errorString();
        return;
    }

    QJsonObject payload;
    payload.insert(QStringLiteral("type"), QStringLiteral("scenario/select"));
    payload.insert(QStringLiteral("name"), name);
    const QByteArray message = QJsonDocument(payload).toJson(QJsonDocument::Compact) + '\n';
    if (controlSocket->write(message) == -1 || !controlSocket->waitForBytesWritten(1000)) {
        qWarning() << "Scenario control send failed:" << controlSocket->errorString();
    }
    controlSocket->disconnectFromHost();
}

void TcpClient::connectFromConfig() {
    QFile file(QStringLiteral(":/icons/config.json"));
    if (!file.open(QIODevice::ReadOnly)) {
        setConnectionStatus(QStringLiteral("Missing config"));
        qWarning() << "Unable to open config.json from resources";
        return;
    }

    const QJsonObject json = QJsonDocument::fromJson(file.readAll()).object();
    const QString ip = json.value(QStringLiteral("server_ip")).toString(QStringLiteral("127.0.0.1"));
    const int port = json.value(QStringLiteral("server_port")).toInt(9998);
    connectTo(ip, port);
}

void TcpClient::setConnectionStatus(const QString &status) {
    if (connectionStatus_ == status) {
        return;
    }
    connectionStatus_ = status;
    emit connectionStatusChanged(connectionStatus_);
}

void TcpClient::onReadyRead() {
    buffer_.append(socket_.readAll());

    int newlineIndex = -1;
    while ((newlineIndex = buffer_.indexOf('\n')) != -1) {
        // Python 브리지가 newline-delimited JSON을 보내므로 줄 단위로 끊어 처리
        const QByteArray line = buffer_.left(newlineIndex).trimmed();
        buffer_.remove(0, newlineIndex + 1);
        processLine(line);
    }
}

void TcpClient::processLine(const QByteArray &line) {
    if (line.isEmpty() || !line.startsWith('{')) {
        return;
    }

    // 한 줄이 완전한 JSON object인지 확인한 뒤, 세부 payload를 항목별로 분배
    QJsonParseError error;
    const QJsonDocument doc = QJsonDocument::fromJson(line, &error);
    if (error.error != QJsonParseError::NoError || !doc.isObject()) {
        qWarning() << "JSON parse error:" << error.errorString() << line.left(120);
        return;
    }

    const QJsonObject object = doc.object();
    const int frameWidth = object.value(QStringLiteral("width")).toInt(800);

    publishTelemetry(object);
    publishSpeedRecommendation(object);
    publishSimulatedBrakeLed(object);
    publishScenarioCatalog(object);
    publishLaneStatus(object, frameWidth);
    publishLaneData(object, frameWidth);
    publishLaneModel(object);
    publishObjects(object);
}

void TcpClient::publishSpeedRecommendation(const QJsonObject &object) {
    const QString mode = object.value(QStringLiteral("speed_control_mode")).toString();
    if ((mode != QStringLiteral("advisory") && mode != QStringLiteral("distance")) ||
        !object.contains(QStringLiteral("recommended_speed_kmh"))) {
        return;
    }

    emit speedRecommendationUpdated(
        object.value(QStringLiteral("recommended_speed_kmh")).toDouble(),
        object.value(QStringLiteral("proximity_status")).toString(),
        object.value(QStringLiteral("closest_object_y_ratio")).toDouble(-1.0));
}

void TcpClient::publishSimulatedBrakeLed(const QJsonObject &object) {
    if (!object.contains(QStringLiteral("brake_led_simulated"))) {
        return;
    }
    emit simulatedBrakeLedUpdated(object.value(QStringLiteral("brake_led_simulated")).toBool());
}

void TcpClient::publishTelemetry(const QJsonObject &object) {
    const bool hasPowertrainTelemetry =
        object.contains(QStringLiteral("rpm")) ||
        object.contains(QStringLiteral("fuel_l"));
    const bool hasSteeringTelemetry = object.contains(QStringLiteral("steering"));

    if (hasPowertrainTelemetry) {
        // powertrain 계열 telemetry가 오면 마지막 값을 캐시하고 계기판 전체를 갱신
        lastTelemetryReceivedMs_ = QDateTime::currentMSecsSinceEpoch();
        lastRpm_ = object.value(QStringLiteral("rpm")).toDouble(lastRpm_);
        lastSpeedKmh_ = object.value(QStringLiteral("speed_kmh")).toDouble(lastSpeedKmh_);
        lastFuelLiters_ = object.value(QStringLiteral("fuel_l")).toDouble(lastFuelLiters_);
        lastSteering_ = object.value(QStringLiteral("steering")).toDouble(lastSteering_);
        emit telemetryUpdated(lastRpm_, lastSpeedKmh_, lastFuelLiters_, lastSteering_);
    } else if (hasSteeringTelemetry) {
        // steering만 따로 와도 기존 rpm/speed/fuel 캐시와 합쳐 UI에 다시 알림
        lastTelemetryReceivedMs_ = QDateTime::currentMSecsSinceEpoch();
        lastSteering_ = object.value(QStringLiteral("steering")).toDouble(lastSteering_);
        emit telemetryUpdated(lastRpm_, lastSpeedKmh_, lastFuelLiters_, lastSteering_);
    }
}

void TcpClient::publishScenarioCatalog(const QJsonObject &object) {
    if (object.contains(QStringLiteral("scenario_name")) || object.contains(QStringLiteral("scenario_list"))) {
        emit scenarioCatalogUpdated(
            object.value(QStringLiteral("scenario_name")).toString(),
            QString::fromUtf8(QJsonDocument(object.value(QStringLiteral("scenario_list")).toArray()).toJson(QJsonDocument::Compact)));
    }
}

void TcpClient::publishLaneStatus(const QJsonObject &object, int frameWidth) {
    bool laneHasObject[5] = {false, false, false, false, false};
    const QJsonArray laneStatus = object.value(QStringLiteral("lane_status")).toArray();
    if (!laneStatus.isEmpty()) {
        // Python에서 lane_status를 직접 보내면 그 값을 우선 사용
        for (int lane = 0; lane < 5 && lane < laneStatus.size(); ++lane) {
            laneHasObject[lane] = laneStatus.at(lane).toBool(false);
        }
    } else {
        // lane_status가 없으면 객체 bbox 중심 x 위치로 5개 lane 점유 상태를 대략 추정
        const QJsonArray objects = object.value(QStringLiteral("objects")).toArray();
        for (const QJsonValue &objectValue : objects) {
            if (!objectValue.isObject()) {
                continue;
            }
            const QJsonObject objectItem = objectValue.toObject();
            const double xMin = objectItem.value(QStringLiteral("x_min")).toDouble();
            const double xMax = objectItem.value(QStringLiteral("x_max")).toDouble();
            const double centerX = (xMin + xMax) * 0.5;
            int laneIndex = int(centerX * 5.0 / double(frameWidth > 0 ? frameWidth : 1));
            laneIndex = qMax(0, qMin(4, laneIndex));
            laneHasObject[laneIndex] = true;
        }
    }

    QJsonArray laneStatusJson;
    for (int lane = 0; lane < 5; ++lane) {
        laneStatusJson.append(laneHasObject[lane]);
    }
    emit laneStatusUpdated(QString::fromUtf8(QJsonDocument(laneStatusJson).toJson(QJsonDocument::Compact)));
}

void TcpClient::publishLaneData(const QJsonObject &object, int frameWidth) {
    QJsonArray normalizedLanes = QJsonArray{QJsonArray{}, QJsonArray{}, QJsonArray{}, QJsonArray{}};
    const QJsonArray lanes = object.value(QStringLiteral("lanes")).toArray();
    for (int laneIdx = 0; laneIdx < lanes.size(); ++laneIdx) {
        const QJsonValue laneValue = lanes.at(laneIdx);
        if (laneValue.isArray()) {
            if (laneIdx < 4) {
                normalizedLanes.replace(laneIdx, laneValue.toArray());
            }
            continue;
        }
        if (!laneValue.isObject()) {
            continue;
        }

        const QJsonObject laneObject = laneValue.toObject();
        const int laneId = laneObject.value(QStringLiteral("lane_id")).toInt(-1);
        if (laneId < 0 || laneId >= 4) {
            continue;
        }

        // 최신 payload는 lane_id와 points를 가진 object 배열 구조를 사용
        normalizedLanes.replace(laneId, laneObject.value(QStringLiteral("points")).toArray());
    }

    const QJsonArray laneLines = object.value(QStringLiteral("lane_lines")).toArray();
    const QJsonArray displayLaneLines = laneLines.isEmpty() ? normalizedLanes : laneLines;
    emit laneDataUpdated(QString::fromUtf8(QJsonDocument(normalizedLanes).toJson(QJsonDocument::Compact)),
                         QString::fromUtf8(QJsonDocument(displayLaneLines).toJson(QJsonDocument::Compact)),
                         frameWidth,
                         object.value(QStringLiteral("height")).toInt(480));
}

void TcpClient::publishLaneModel(const QJsonObject &object) {
    // lane_model 내부 정보에 centerline/raw_path를 합쳐 3D scene 입력으로 보냄
    QJsonObject laneModelObject = object.value(QStringLiteral("lane_model")).toObject();
    laneModelObject.insert(QStringLiteral("centerline"), object.value(QStringLiteral("centerline")).toArray());
    laneModelObject.insert(QStringLiteral("raw_path"), object.value(QStringLiteral("raw_path")).toArray());
    emit laneModelUpdated(QString::fromUtf8(QJsonDocument(laneModelObject).toJson(QJsonDocument::Compact)));
}

void TcpClient::publishObjects(const QJsonObject &object) {
    // Qt 3D 장면은 BEV 기준 객체만 사용하므로 bev_objects만 별도로 전달
    const QJsonArray bevObjects = object.value(QStringLiteral("bev_objects")).toArray();
    emit objectDataUpdated(QString::fromUtf8(QJsonDocument(bevObjects).toJson(QJsonDocument::Compact)));
}
