import QtQuick 2.12
import QtQuick.Controls 1.4
import QtQuick.Controls.Styles 1.4
import QtQuick.Window 2.12
import QtQuick.Extras 1.4
import "theme"
import "components"
import "components/drawers"

ApplicationWindow {
    id: root
    width: 1920; height: 1080
    visible: true
    color: Theme.bgPrimary
    title: "TOPST_DashBoard"
    property int sidePanelWidth: 340

    // TcpClient에서 들어온 실시간 값을 루트 상태로 보관하고 각 패널이 이를 참조한다.
    property real speedKph: 0
    property real rpm: 0
    property real fuelRatio: 0.72
    property real temperatureRatio: 0.42
    property real steering: 0
    property real steeringTarget: 0
    property real recommendedSpeedKmh: -1
    property string proximityStatus: "unavailable"
    property real closestObjectYRatio: -1
    property bool simulatedBrakeLed: false
    property int turnSignal: 0
    property string connectionState: "Idle"
    property string serverEndpoint: "Unknown"
    property var lanePolylines: [[], [], [], []]
    property var detectedLaneLines: []
    property var laneModel: ({})
    property var bevObjects: []
    property int laneFrameWidth: 800
    property int laneFrameHeight: 480
    property string currentTime: ""
    property string scenarioName: "Default Scenario"
    property var scenarioList: []
    property bool scenarioPickerOpen: false

    Timer {
        // 시계 표시는 10초 단위로만 갱신해 불필요한 UI 업데이트를 줄인다.
        interval: 10000; running: true; repeat: true; triggeredOnStart: true
        onTriggered: root.currentTime = Qt.formatDateTime(new Date(), "hh:mm")
    }

    Timer {
        // steering 원시값을 바로 쓰지 않고 약간 보간해 계기판 움직임을 부드럽게 만든다.
        interval: 33
        running: true
        repeat: true
        onTriggered: {
            root.steering += (root.steeringTarget - root.steering) * 0.18
            if (Math.abs(root.steeringTarget - root.steering) < 0.1)
                root.steering = root.steeringTarget
            root.turnSignal = root.steering > 8 ? Qt.RightArrow : (root.steering < -8 ? Qt.LeftArrow : 0)
        }
    }

    function countObjectsInLane(lid) {
        // 특정 lane에 속한 객체 수를 빠르게 집계할 때 사용한다.
        var c = 0
        for (var i = 0; i < bevObjects.length; ++i)
            if (Number(bevObjects[i].lane_id) === lid) c++
        return c
    }
    function closestObject() {
        // BEV y가 가장 큰 객체를 전방에 가장 가까운 객체로 간주한다.
        if (!bevObjects.length) return null
        var b = bevObjects[0]
        for (var i = 1; i < bevObjects.length; ++i)
            if (Number(bevObjects[i].bev_y) > Number(b.bev_y)) b = bevObjects[i]
        return b
    }

    Connections {
        target: tcpClient
        // Python 브리지 -> TcpClient -> root property -> 각 패널로 이어지는 데이터 연결 지점이다.
        function onTelemetryUpdated(r, s, f, st) {
            root.speedKph = Math.max(0, Math.min(70, s))
            root.rpm = Math.max(0, Math.min(8000, r))
            root.fuelRatio = Math.max(0, Math.min(1, f / 1400.0))
            root.temperatureRatio = Math.max(0.2, Math.min(1, 0.28 + (r / 8000) * 0.5 + (s / 280) * 0.22))
            root.steeringTarget = st
        }
        function onSpeedRecommendationUpdated(speed, status, yRatio) {
            root.recommendedSpeedKmh = speed
            root.proximityStatus = status
            root.closestObjectYRatio = yRatio
        }
        function onSimulatedBrakeLedUpdated(active) { root.simulatedBrakeLed = active }
        function onObjectDataUpdated(j) { try { root.bevObjects = JSON.parse(j) } catch(e) { root.bevObjects = [] } }
        function onLaneDataUpdated(j, allLinesJson, w, h) { try { root.lanePolylines = JSON.parse(j) } catch(e) { root.lanePolylines = [[], [], [], []] }; try { root.detectedLaneLines = JSON.parse(allLinesJson) } catch(e) { root.detectedLaneLines = root.lanePolylines }; root.laneFrameWidth = Math.max(1, w); root.laneFrameHeight = Math.max(1, h) }
        function onLaneModelUpdated(j) { try { root.laneModel = JSON.parse(j) } catch(e) { root.laneModel = ({}) } }
        function onConnectionStatusChanged(s) { root.connectionState = s }
        function onEndpointChanged(e) { root.serverEndpoint = e }
        function onScenarioCatalogUpdated(currentName, scenarioListJson) {
            root.scenarioName = currentName && currentName.length ? currentName : root.scenarioName
            try { root.scenarioList = JSON.parse(scenarioListJson) } catch (e) { root.scenarioList = [] }
        }
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#18222c" }
            GradientStop { position: 0.3; color: "#10181f" }
            GradientStop { position: 0.7; color: "#0c1218" }
            GradientStop { position: 1.0; color: "#080c10" }
        }
    }

    TopStatusBar {
        id: topBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 56
        z: 30
    }

    Row {
        id: mainContent
        anchors.top: topBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: replayBar.top
        anchors.margins: 10
        spacing: 10

        // 좌측 계기판, 중앙 3D scene, 우측 파워트레인 패널의 3단 구조를 유지한다.
        LeftClusterPanel {
            width: root.sidePanelWidth
            height: parent.height
        }

        CenterSceneView {
            width: parent.width - root.sidePanelWidth - root.sidePanelWidth - mainContent.spacing * 2
            height: parent.height
            recommendedSpeedKmh: root.recommendedSpeedKmh
            proximityStatus: root.proximityStatus
        }

        RightInfoPanel {
            width: root.sidePanelWidth
            height: parent.height
        }
    }

    ScenarioReplayBar {
        id: replayBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: bottomDock.top
        height: app.driveMode > 0 ? 44 : 0
        visible: app.driveMode > 0
        Behavior on height { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
    }

    BottomActionDock {
        id: bottomDock
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 68
        z: 30
        onActionTriggered: function(index, label) {
            // Scenario 버튼만 별도 다이얼로그를 열고, 나머지는 active tab 전환으로 처리한다.
            if (label === "Scenario") {
                root.scenarioPickerOpen = !root.scenarioPickerOpen
                return
            }
            app.activeTab = index
        }
    }

    ScenarioPickerDialog {
        anchors.fill: parent
        z: 80
        open: root.scenarioPickerOpen
        currentScenario: root.scenarioName
        scenarios: root.scenarioList
        onClosed: root.scenarioPickerOpen = false
        onScenarioSelected: function(name) {
            // 시나리오 선택은 control socket 명령으로 Python 브리지에 전달된다.
            tcpClient.selectScenario(name)
            root.scenarioPickerOpen = false
        }
    }

    ObjectInspectorDrawer {
        id: inspectorDrawer
        anchors.top: topBar.bottom
        anchors.bottom: bottomDock.top
        anchors.right: parent.right
        width: app.inspectorOpen ? 360 : 0
        z: 50
        clip: true
        Behavior on width { NumberAnimation { duration: 250; easing.type: Easing.OutCubic } }
    }

    AlertDrawer {
        id: alertDrawer
        anchors.top: topBar.bottom
        anchors.bottom: bottomDock.top
        anchors.right: parent.right
        width: app.alertDrawerOpen ? 380 : 0
        z: 50
        clip: true
        Behavior on width { NumberAnimation { duration: 250; easing.type: Easing.OutCubic } }
    }
}
