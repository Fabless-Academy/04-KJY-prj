import QtQuick 2.12
import "../theme"

Rectangle {
    color: Theme.rgba("#0b1118", 0.95)
    Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: Theme.borderDefault }

    Row {
        anchors.centerIn: parent; spacing: 12

        Repeater {
            model: [
                { icon: "\u23EE", action: "stepBack" },
                { icon: app.replayPlaying ? "\u23F8" : "\u25B6", action: "playPause" },
                { icon: "\u23ED", action: "stepFwd" }
            ]
            delegate: Rectangle {
                width: 28; height: 24; radius: 6; color: Theme.rgba("#ffffff", 0.04); border.color: Theme.borderDefault; border.width: 1
                anchors.verticalCenter: parent.verticalCenter
                Text { anchors.centerIn: parent; text: modelData.icon; color: Theme.accentCyan; font.pixelSize: 12 }
                MouseArea {
                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (modelData.action === "playPause") app.replayPlaying = !app.replayPlaying
                        else if (modelData.action === "stepBack") app.replayStep(-1)
                        else app.replayStep(1)
                    }
                }
            }
        }

        Rectangle {
            width: 400; height: 6; radius: 3; color: Theme.bgCard; anchors.verticalCenter: parent.verticalCenter
            Rectangle {
                width: parent.width * app.replayPosition; height: parent.height; radius: 3
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: Theme.accentCyan }
                    GradientStop { position: 1.0; color: Theme.accentBlue }
                }
            }
            MouseArea {
                anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                onClicked: app.replayPosition = mouse.x / width
            }
        }

        Text { text: Math.round(app.replayPosition * 100) + "%"; color: Theme.textSecondary; font.pixelSize: Theme.fontSm; anchors.verticalCenter: parent.verticalCenter }
    }
}
