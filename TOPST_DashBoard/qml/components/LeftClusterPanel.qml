import QtQuick 2.12
import QtQuick.Extras 1.4
import QtQuick.Controls.Styles 1.4
import "../theme"
import "gauges"

Rectangle {
    id: panel
    radius: Theme.radiusXl
    gradient: Gradient {
        GradientStop { position: 0.0; color: Theme.gradPanelTop }
        GradientStop { position: 0.4; color: Theme.gradPanelMid }
        GradientStop { position: 1.0; color: Theme.gradPanelBottom }
    }
    border.color: Theme.borderDefault; border.width: 1

    Rectangle { anchors.top: parent.top; anchors.topMargin: 1; anchors.left: parent.left; anchors.leftMargin: 12; anchors.right: parent.right; anchors.rightMargin: 12; height: 1; radius: 1; color: Theme.rgba("#ffffff", 0.04) }

    Column {
        anchors.fill: parent; anchors.margins: Theme.spacingXl
        spacing: Theme.spacingSm

        // 좌측 패널은 운전자 시점의 주 계기판 역할을 한다.
        Text { text: "Speed"; color: Theme.textPrimary; font.pixelSize: Theme.fontTitle+8; font.bold: true }
        Text { text: "Realtime powertrain cluster"; color: Theme.textSecondary; font.pixelSize: Theme.fontMd }

        Item { width: 1; height: 4 }

        CircularGauge {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 280; height: 280
            // speedKph는 root에서 clamp된 값을 받아 속도계 needle을 구동한다.
            value: root.speedKph; maximumValue: 70
            style: DashboardGaugeStyle {}
            Behavior on value { NumberAnimation { duration: 120; easing.type: Easing.OutQuad } }
        }

        Item { width: 1; height: 4 }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Theme.spacingMd

            Repeater {
                // 조향, 방향지시 상태와 감속 권고에 따른 시뮬레이션 LED를 표시한다.
                model: [
                    { label: "STEER", value: root.steering.toFixed(1) + "\u00b0", accent: false },
                    { label: "SIGNAL", value: root.turnSignal === Qt.LeftArrow ? "\u25C0" : root.turnSignal === Qt.RightArrow ? "\u25B6" : "-", accent: true },
                    { label: "BRAKE SIM", value: root.simulatedBrakeLed ? "ON" : "OFF", accent: root.simulatedBrakeLed }
                ]
                delegate: Rectangle {
                    width: modelData.label === "BRAKE SIM" ? 88 : 132; height: 84; radius: Theme.radiusLg
                    gradient: Gradient { GradientStop { position: 0.0; color: Theme.gradCardTop } GradientStop { position: 1.0; color: Theme.gradCardBottom } }
                    border.color: Theme.borderDefault
                    Rectangle { anchors.top: parent.top; anchors.topMargin: 1; anchors.left: parent.left; anchors.leftMargin: 6; anchors.right: parent.right; anchors.rightMargin: 6; height: 1; radius: 1; color: Theme.rgba("#ffffff", 0.04) }
                    Column {
                        anchors.centerIn: parent; spacing: 2
                        Text { text: modelData.label; color: Theme.textSecondary; font.pixelSize: Theme.fontMd; anchors.horizontalCenter: parent.horizontalCenter }
                        Text { visible: modelData.label !== "BRAKE SIM"; text: modelData.value; color: modelData.accent ? Theme.textValue : Theme.textPrimary; font.pixelSize: Theme.fontXl + 4; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter }
                        Row {
                            visible: modelData.label === "BRAKE SIM"
                            anchors.horizontalCenter: parent.horizontalCenter
                            spacing: 5
                            Rectangle {
                                width: 10; height: 10; radius: 5
                                anchors.verticalCenter: parent.verticalCenter
                                color: root.simulatedBrakeLed ? Theme.statusRed : Theme.textMuted
                            }
                            Text {
                                text: modelData.value
                                color: root.simulatedBrakeLed ? Theme.statusRed : Theme.textMuted
                                font.pixelSize: Theme.fontMd
                                font.bold: true
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            width: parent.width; height: 56; radius: Theme.radiusLg
            gradient: Gradient { GradientStop { position: 0.0; color: Theme.gradCardTop } GradientStop { position: 1.0; color: Theme.gradCardBottom } }
            border.color: Theme.borderDefault
            Text { anchors.centerIn: parent; text: "Vehicle State"; color: Theme.textPrimary; font.pixelSize: Theme.fontLg + 4; font.bold: true }
        }

        Rectangle {
            width: parent.width; height: 40; radius: Theme.radiusMd
            gradient: Gradient { GradientStop { position: 0.0; color: "#1a2a38" } GradientStop { position: 1.0; color: "#122028" } }
            border.color: Theme.borderDefault
            // 연결 상태 문자열은 TcpClient가 관리하는 상태를 그대로 보여준다.
            Text { anchors.centerIn: parent; text: root.connectionState; color: Theme.textValue; font.pixelSize: Theme.fontMd; font.bold: true }
        }

        Row {
            visible: app.driveMode >= 1
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 8
            Repeater {
                // drive mode 선택은 AppController 상태를 직접 바꾸는 단순 토글 UI다.
                model: ["Drive", "Teach", "Debug"]
                delegate: Rectangle {
                    width: 76; height: 30; radius: 15
                    color: app.driveMode === index ? Theme.rgba("#59c0cd", 0.15) : "transparent"
                    border.color: app.driveMode === index ? Theme.accentCyan : Theme.borderDefault; border.width: 1
                    Text { anchors.centerIn: parent; text: modelData; color: app.driveMode === index ? Theme.accentCyan : Theme.textMuted; font.pixelSize: Theme.fontSm; font.bold: true }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: app.driveMode = index }
                }
            }
        }
    }
}
