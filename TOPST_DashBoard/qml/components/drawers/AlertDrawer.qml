import QtQuick 2.12
import "../../theme"

Rectangle {
    id: drawer
    gradient: Gradient {
        GradientStop { position: 0.0; color: "#1a1218" }
        GradientStop { position: 1.0; color: "#0e0c10" }
    }
    border.color: Theme.borderDefault; border.width: 1

    Column {
        anchors.fill: parent; anchors.margins: Theme.spacingXl
        spacing: Theme.spacingMd
        visible: drawer.width > 50

        Row {
            width: parent.width
            Text { text: "Alert Center"; color: Theme.textPrimary; font.pixelSize: Theme.fontLg; font.bold: true }
            Item { width: parent.width - 160; height: 1 }
            Rectangle {
                width: 24; height: 24; radius: 12; color: Theme.rgba("#ffffff", 0.05); border.color: Theme.borderDefault
                Text { anchors.centerIn: parent; text: "\u2715"; color: Theme.textMuted; font.pixelSize: 10 }
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: app.alertDrawerOpen = false }
            }
        }

        Rectangle { width: parent.width; height: 1; color: Theme.borderDefault }

        Text {
            visible: app.alertCount === 0
            text: "No active alerts"
            color: Theme.textMuted; font.pixelSize: Theme.fontSm
        }

        Flickable {
            width: parent.width; height: parent.height - 60
            contentHeight: alertCol.height; clip: true

            Column {
                id: alertCol; width: parent.width; spacing: 6

                Repeater {
                    model: app.alerts()
                    delegate: Rectangle {
                        width: parent.width; height: 50; radius: Theme.radiusMd
                        color: modelData.severity === "error" ? Theme.rgba("#ef4444", 0.08) : modelData.severity === "warn" ? Theme.rgba("#f59e0b", 0.08) : Theme.rgba("#ffffff", 0.03)
                        border.color: modelData.severity === "error" ? Theme.rgba("#ef4444", 0.3) : modelData.severity === "warn" ? Theme.rgba("#f59e0b", 0.3) : Theme.borderDefault

                        Column {
                            x: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 2
                            Text { text: modelData.message || ""; color: Theme.textPrimary; font.pixelSize: Theme.fontSm }
                            Text { text: (modelData.time || "") + " \u2022 " + (modelData.severity || ""); color: Theme.textMuted; font.pixelSize: Theme.fontXs }
                        }

                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: app.dismissAlert(index)
                        }
                    }
                }
            }
        }
    }
}
