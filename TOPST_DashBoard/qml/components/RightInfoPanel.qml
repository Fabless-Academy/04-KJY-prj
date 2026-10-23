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

        // 우측 패널은 RPM, 연료, 온도 중심의 파워트레인 상태를 모아서 보여준다.
        Text { text: "Motor RPM"; color: Theme.textPrimary; font.pixelSize: Theme.fontTitle+8; font.bold: true }
        Text { text: "Engine, fuel and thermal status"; color: Theme.textSecondary; font.pixelSize: Theme.fontMd }

        Item { width: 1; height: 4 }

        CircularGauge {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 280; height: 280
            // TachometerStyle은 rpm 실값을 별도로 받아 눈금 텍스트와 needle 표시를 맞춘다.
            value: root.rpm * 0.001; maximumValue: 8
            style: TachometerStyle { rpmValue: root.rpm }
            Behavior on value { NumberAnimation { duration: 120; easing.type: Easing.OutQuad } }
        }

        Item { width: 1; height: 4 }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter; spacing: 12

            CircularGauge {
                // 연료/온도는 0~1 정규화 비율로 표시해 다양한 입력 스케일에 대응한다.
                width: 128; height: 96; value: root.fuelRatio; maximumValue: 1
                style: IconGaugeStyle { icon: ""; minWarningColor: Qt.rgba(0.5, 0, 0, 1)
                    tickmarkLabel: Text { color: "white"; visible: styleData.value === 0 || styleData.value === 1; font.pixelSize: 11; text: styleData.value === 0 ? "E" : (styleData.value === 1 ? "F" : "") } }
            }
            CircularGauge {
                width: 128; height: 96; value: root.temperatureRatio; maximumValue: 1
                style: IconGaugeStyle { icon: ""; maxWarningColor: Qt.rgba(0.5, 0, 0, 1)
                    tickmarkLabel: Text { color: "white"; visible: styleData.value === 0 || styleData.value === 1; font.pixelSize: 11; text: styleData.value === 0 ? "C" : (styleData.value === 1 ? "H" : "") } }
            }
        }

        Rectangle {
            width: parent.width; height: 136; radius: Theme.radiusLg
            gradient: Gradient { GradientStop { position: 0.0; color: "#192838" } GradientStop { position: 0.5; color: "#13202b" } GradientStop { position: 1.0; color: "#0e1820" } }
            border.color: "#223243"
            Rectangle { anchors.top: parent.top; anchors.topMargin: 1; anchors.left: parent.left; anchors.leftMargin: 8; anchors.right: parent.right; anchors.rightMargin: 8; height: 1; radius: 1; color: Theme.rgba("#ffffff", 0.04) }

            Column {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10
                Text { text: "Telemetry Summary"; color: Theme.textPrimary; font.pixelSize: Theme.fontLg + 4; font.bold: true }
                Row {
                    spacing: 10
                    width: parent.width
                    Repeater {
                        // 하단 요약 카드는 fuel/thermal/engine을 동일 폭 3칸으로 정렬한다.
                        model: [
                            { label: "Fuel", value: Math.round(root.fuelRatio * 100) + "%" },
                            { label: "Thermal", value: Math.round(root.temperatureRatio * 100) + "%" },
                            { label: "Engine", value: Math.round(root.rpm) + " rpm" }
                        ]
                        delegate: Rectangle {
                            width: (parent.width - 20) / 3; height: 60; radius: Theme.radiusSm
                            gradient: Gradient { GradientStop { position: 0.0; color: Theme.gradCardTop } GradientStop { position: 1.0; color: Theme.gradCardBottom } }
                            border.color: Theme.borderDefault
                            Column { anchors.centerIn: parent; spacing: 0
                                Text { text: modelData.label; color: Theme.textSecondary; font.pixelSize: Theme.fontSm; anchors.horizontalCenter: parent.horizontalCenter }
                                Text { text: modelData.value; color: Theme.textPrimary; font.pixelSize: Theme.fontSm; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter }
                            }
                        }
                    }
                }
            }
        }

        Column {
            visible: app.driveMode >= 2
            width: parent.width; spacing: 4
            // Debug 성격의 health 정보는 Debug 모드에서만 노출한다.
            Text { text: "System Health"; color: Theme.textSecondary; font.pixelSize: Theme.fontMd; font.bold: true }
            Repeater {
                model: [ { label: "Camera", ok: true }, { label: "LiDAR", ok: false }, { label: "CAN Bus", ok: root.connectionState === "Connected" } ]
                delegate: Row {
                    spacing: 8
                    Rectangle { width: 8; height: 8; radius: 4; color: modelData.ok ? Theme.statusGreen : Theme.statusRed; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: modelData.label; color: Theme.textSecondary; font.pixelSize: Theme.fontSm }
                    Text { text: modelData.ok ? "OK" : "N/A"; color: modelData.ok ? Theme.statusGreen : Theme.statusRed; font.pixelSize: Theme.fontSm; font.bold: true }
                }
            }
        }
    }
}
