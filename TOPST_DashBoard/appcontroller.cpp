#include "appcontroller.h"
#include <QDateTime>

AppController::AppController(QObject *parent) : QObject(parent) {}

// 대부분의 setter는 값이 실제로 바뀐 경우에만 signal을 내보내 불필요한 QML 재평가를 줄임
void AppController::setDriveMode(int v)         { if (m_driveMode != v) { m_driveMode = v; emit driveModeChanged(); } }
void AppController::setOverlayLane(bool v)       { if (m_overlayLane != v) { m_overlayLane = v; emit overlayLaneChanged(); } }
void AppController::setOverlayObject(bool v)     { if (m_overlayObject != v) { m_overlayObject = v; emit overlayObjectChanged(); } }
void AppController::setOverlayLabel(bool v)      { if (m_overlayLabel != v) { m_overlayLabel = v; emit overlayLabelChanged(); } }
void AppController::setOverlayPath(bool v)       { if (m_overlayPath != v) { m_overlayPath = v; emit overlayPathChanged(); } }
void AppController::setOverlaySafetyZone(bool v) { if (m_overlaySafetyZone != v) { m_overlaySafetyZone = v; emit overlaySafetyZoneChanged(); } }
void AppController::setSelectedObjectIndex(int v){ if (m_selectedObjectIndex != v) { m_selectedObjectIndex = v; emit selectedObjectIndexChanged(); } }
void AppController::setInspectorOpen(bool v)     { if (m_inspectorOpen != v) { m_inspectorOpen = v; emit inspectorOpenChanged(); } }
void AppController::setAlertDrawerOpen(bool v)   { if (m_alertDrawerOpen != v) { m_alertDrawerOpen = v; emit alertDrawerOpenChanged(); } }
void AppController::setActiveTab(int v)          { if (m_activeTab != v) { m_activeTab = v; emit activeTabChanged(); } }
void AppController::setReplayPlaying(bool v)     { if (m_replayPlaying != v) { m_replayPlaying = v; emit replayPlayingChanged(); } }
void AppController::setReplayPosition(double v)  { if (m_replayPosition != v) { m_replayPosition = qBound(0.0, v, 1.0); emit replayPositionChanged(); } }

void AppController::toggleOverlay(const QString &name) {
    // 문자열 이름으로 overlay 토글을 묶어 QML 버튼에서 공통 호출
    if (name == "lane")       setOverlayLane(!m_overlayLane);
    else if (name == "object") setOverlayObject(!m_overlayObject);
    else if (name == "label")  setOverlayLabel(!m_overlayLabel);
    else if (name == "path")   setOverlayPath(!m_overlayPath);
    else if (name == "safety") setOverlaySafetyZone(!m_overlaySafetyZone);
}

void AppController::selectObject(int index) {
    // 객체 선택 시 inspector drawer도 함께 여는 UX 정책을 적용
    setSelectedObjectIndex(index);
    setInspectorOpen(index >= 0);
}

void AppController::clearSelection() {
    setSelectedObjectIndex(-1);
    setInspectorOpen(false);
}

void AppController::replayStep(int delta) {
    // 재생 위치는 0.01 단위로 미세 조정
    setReplayPosition(m_replayPosition + delta * 0.01);
}

void AppController::pushAlert(const QString &severity, const QString &message) {
    // 최근 alert를 앞쪽에 쌓고, 너무 길어지면 오래된 항목부터 버림
    QVariantMap alert;
    alert["severity"] = severity;
    alert["message"] = message;
    alert["time"] = QDateTime::currentDateTime().toString("hh:mm:ss");
    m_alerts.prepend(alert);
    if (m_alerts.size() > 50) m_alerts.removeLast();
    emit alertCountChanged();
}

void AppController::dismissAlert(int index) {
    if (index >= 0 && index < m_alerts.size()) {
        m_alerts.removeAt(index);
        emit alertCountChanged();
    }
}

QString AppController::modeName() const {
    // 내부 enum 값을 화면에 표시할 문자열로 변환
    switch (m_driveMode) {
    case Drive: return "Drive";
    case Teach: return "Teach";
    case Debug: return "Debug";
    default: return "Unknown";
    }
}
