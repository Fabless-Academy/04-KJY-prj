#pragma once
#include <QObject>
#include <QVariantList>
#include <QVariantMap>

class AppController : public QObject {
    Q_OBJECT

    // Q_PROPERTY들은 QML에서 직접 바인딩하는 UI 상태 저장소 역할
    Q_PROPERTY(int driveMode READ driveMode WRITE setDriveMode NOTIFY driveModeChanged)
    Q_PROPERTY(bool overlayLane READ overlayLane WRITE setOverlayLane NOTIFY overlayLaneChanged)
    Q_PROPERTY(bool overlayObject READ overlayObject WRITE setOverlayObject NOTIFY overlayObjectChanged)
    Q_PROPERTY(bool overlayLabel READ overlayLabel WRITE setOverlayLabel NOTIFY overlayLabelChanged)
    Q_PROPERTY(bool overlayPath READ overlayPath WRITE setOverlayPath NOTIFY overlayPathChanged)
    Q_PROPERTY(bool overlaySafetyZone READ overlaySafetyZone WRITE setOverlaySafetyZone NOTIFY overlaySafetyZoneChanged)
    Q_PROPERTY(int selectedObjectIndex READ selectedObjectIndex WRITE setSelectedObjectIndex NOTIFY selectedObjectIndexChanged)
    Q_PROPERTY(bool inspectorOpen READ inspectorOpen WRITE setInspectorOpen NOTIFY inspectorOpenChanged)
    Q_PROPERTY(bool alertDrawerOpen READ alertDrawerOpen WRITE setAlertDrawerOpen NOTIFY alertDrawerOpenChanged)
    Q_PROPERTY(int activeTab READ activeTab WRITE setActiveTab NOTIFY activeTabChanged)
    Q_PROPERTY(bool replayPlaying READ replayPlaying WRITE setReplayPlaying NOTIFY replayPlayingChanged)
    Q_PROPERTY(double replayPosition READ replayPosition WRITE setReplayPosition NOTIFY replayPositionChanged)
    Q_PROPERTY(int alertCount READ alertCount NOTIFY alertCountChanged)

public:
    enum DriveMode { Drive = 0, Teach = 1, Debug = 2 };
    Q_ENUM(DriveMode)

    explicit AppController(QObject *parent = nullptr);

    int driveMode() const { return m_driveMode; }
    bool overlayLane() const { return m_overlayLane; }
    bool overlayObject() const { return m_overlayObject; }
    bool overlayLabel() const { return m_overlayLabel; }
    bool overlayPath() const { return m_overlayPath; }
    bool overlaySafetyZone() const { return m_overlaySafetyZone; }
    int selectedObjectIndex() const { return m_selectedObjectIndex; }
    bool inspectorOpen() const { return m_inspectorOpen; }
    bool alertDrawerOpen() const { return m_alertDrawerOpen; }
    int activeTab() const { return m_activeTab; }
    bool replayPlaying() const { return m_replayPlaying; }
    double replayPosition() const { return m_replayPosition; }
    int alertCount() const { return m_alerts.size(); }

    void setDriveMode(int v);
    void setOverlayLane(bool v);
    void setOverlayObject(bool v);
    void setOverlayLabel(bool v);
    void setOverlayPath(bool v);
    void setOverlaySafetyZone(bool v);
    void setSelectedObjectIndex(int v);
    void setInspectorOpen(bool v);
    void setAlertDrawerOpen(bool v);
    void setActiveTab(int v);
    void setReplayPlaying(bool v);
    void setReplayPosition(double v);

    // QML 버튼/제스처가 호출하는 고수준 UI 액션
    Q_INVOKABLE void toggleOverlay(const QString &name);
    Q_INVOKABLE void selectObject(int index);
    Q_INVOKABLE void clearSelection();
    Q_INVOKABLE void replayStep(int delta);
    Q_INVOKABLE void pushAlert(const QString &severity, const QString &message);
    Q_INVOKABLE void dismissAlert(int index);
    Q_INVOKABLE QVariantList alerts() const { return m_alerts; }
    Q_INVOKABLE QString modeName() const;

signals:
    // 각 상태 변경은 대응되는 signal을 통해 QML 재바인딩을 유도
    void driveModeChanged();
    void overlayLaneChanged();
    void overlayObjectChanged();
    void overlayLabelChanged();
    void overlayPathChanged();
    void overlaySafetyZoneChanged();
    void selectedObjectIndexChanged();
    void inspectorOpenChanged();
    void alertDrawerOpenChanged();
    void activeTabChanged();
    void replayPlayingChanged();
    void replayPositionChanged();
    void alertCountChanged();

private:
    int m_driveMode = Drive;
    bool m_overlayLane = true;
    bool m_overlayObject = true;
    bool m_overlayLabel = true;
    bool m_overlayPath = true;
    bool m_overlaySafetyZone = false;
    int m_selectedObjectIndex = -1;
    bool m_inspectorOpen = false;
    bool m_alertDrawerOpen = false;
    int m_activeTab = 0;
    bool m_replayPlaying = false;
    double m_replayPosition = 0.0;
    QVariantList m_alerts;
};
