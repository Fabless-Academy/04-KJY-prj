import QtQuick 2.12
import "../theme"

Rectangle {
    id: bar
    gradient: Gradient {
        GradientStop { position: 0.0; color: "#141c26" }
        GradientStop { position: 1.0; color: "#0e151c" }
    }

    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.borderDefault }
    Canvas {
        anchors.bottom: parent.bottom; anchors.bottomMargin: 1
        width: parent.width; height: 2
        onPaint: {
            var ctx = getContext("2d"); ctx.reset()
            var g = ctx.createLinearGradient(0, 0, width, 0)
            g.addColorStop(0.0, "transparent"); g.addColorStop(0.3, "rgba(89,192,205,0.12)")
            g.addColorStop(0.5, "rgba(89,192,205,0.25)"); g.addColorStop(0.7, "rgba(89,192,205,0.12)")
            g.addColorStop(1.0, "transparent"); ctx.fillStyle = g; ctx.fillRect(0, 0, width, height)
        }
    }

    Row {
        x: 20; anchors.verticalCenter: parent.verticalCenter; spacing: 16

        Repeater {
            // 좌측 배지는 현재 모드, 연결 상태, 시나리오 이름을 압축해서 보여준다.
            model: [
                { text: app.modeName(), active: true, w: 110 },
                { text: root.connectionState, active: root.connectionState === "Connected", w: 132 },
                { text: root.scenarioName, active: false, w: 220 }
            ]
            delegate: Rectangle {
                width: modelData.w; height: 34; radius: 17
                gradient: Gradient {
                    GradientStop { position: 0.0; color: modelData.active ? "#1e4450" : "#161e28" }
                    GradientStop { position: 1.0; color: modelData.active ? "#143038" : "#0e151c" }
                }
                border.color: modelData.active ? Theme.accentCyan : Theme.borderDefault; border.width: 1
                anchors.verticalCenter: parent.verticalCenter
                Text { anchors.centerIn: parent; text: modelData.text; color: modelData.active ? "#ebffff" : Theme.textSecondary; font.pixelSize: Theme.fontMd; font.bold: true }
                Rectangle { anchors.top: parent.top; anchors.topMargin: 1; anchors.left: parent.left; anchors.leftMargin: 6; anchors.right: parent.right; anchors.rightMargin: 6; height: 1; radius: 1; color: modelData.active ? Theme.rgba("#59c0cd", 0.2) : Theme.rgba("#ffffff", 0.03) }
            }
        }
    }

    Row {
        anchors.right: parent.right; anchors.rightMargin: 20; anchors.verticalCenter: parent.verticalCenter; spacing: 14

        Text { text: root.currentTime; color: Theme.textPrimary; font.pixelSize: Theme.fontLg; font.bold: true; anchors.verticalCenter: parent.verticalCenter }

        Rectangle { width: 1; height: 22; color: Theme.borderDefault; anchors.verticalCenter: parent.verticalCenter }

        Repeater {
            // overlay 토글은 중앙 3D scene에서 lane/object/path 가시성을 켜고 끈다.
            model: [
                { label: "Lane", key: "lane", on: app.overlayLane },
                { label: "Obj", key: "object", on: app.overlayObject },
                { label: "Path", key: "path", on: app.overlayPath }
            ]
            delegate: Rectangle {
                width: 54; height: 30; radius: 8
                color: modelData.on ? Theme.rgba("#59c0cd", 0.15) : Theme.rgba("#ffffff", 0.03)
                border.color: modelData.on ? Theme.accentCyan : Theme.borderDefault; border.width: 1
                anchors.verticalCenter: parent.verticalCenter
                Text { anchors.centerIn: parent; text: modelData.label; color: modelData.on ? Theme.accentCyan : Theme.textMuted; font.pixelSize: Theme.fontSm; font.bold: true }
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: app.toggleOverlay(modelData.key) }
            }
        }

        Rectangle { width: 1; height: 22; color: Theme.borderDefault; anchors.verticalCenter: parent.verticalCenter }

        Rectangle {
            width: 36; height: 36; radius: 18
            color: app.alertCount > 0 ? Theme.rgba("#ef4444", 0.15) : Theme.rgba("#ffffff", 0.03)
            border.color: app.alertCount > 0 ? Theme.statusRed : Theme.borderDefault; border.width: 1
            anchors.verticalCenter: parent.verticalCenter
            // alert 아이콘은 drawer를 여닫는 진입점이다.
            Text { anchors.centerIn: parent; text: "\u26A0"; color: app.alertCount > 0 ? Theme.statusRed : Theme.textMuted; font.pixelSize: 16 }
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: app.alertDrawerOpen = !app.alertDrawerOpen }
        }
    }
}
