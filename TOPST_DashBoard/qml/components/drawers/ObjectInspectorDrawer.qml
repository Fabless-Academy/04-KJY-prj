import QtQuick 2.12
import "../../theme"

Rectangle {
    id: drawer
    gradient: Gradient {
        GradientStop { position: 0.0; color: "#161e28" }
        GradientStop { position: 1.0; color: "#0c1218" }
    }
    border.color: Theme.borderDefault; border.width: 1

    property var obj: app.selectedObjectIndex >= 0 && app.selectedObjectIndex < root.bevObjects.length ? root.bevObjects[app.selectedObjectIndex] : null

    Column {
        anchors.fill: parent; anchors.margins: Theme.spacingXl
        spacing: Theme.spacingMd
        visible: drawer.width > 50

        Row {
            width: parent.width
            Text { text: "Object Inspector"; color: Theme.textPrimary; font.pixelSize: Theme.fontLg; font.bold: true }
            Item { width: parent.width - 160; height: 1 }
            Rectangle {
                width: 24; height: 24; radius: 12; color: Theme.rgba("#ffffff", 0.05); border.color: Theme.borderDefault
                Text { anchors.centerIn: parent; text: "\u2715"; color: Theme.textMuted; font.pixelSize: 10 }
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: app.clearSelection() }
            }
        }

        Rectangle { width: parent.width; height: 1; color: Theme.borderDefault }

        Column {
            width: parent.width; spacing: Theme.spacingSm
            visible: drawer.obj !== null

            Repeater {
                model: drawer.obj ? [
                    { label: "Track ID", value: String(drawer.obj.track_id || "-") },
                    { label: "Class", value: String(drawer.obj.class_name || "Vehicle") },
                    { label: "Lane ID", value: String(drawer.obj.lane_id || "-") },
                    { label: "BEV X", value: Number(drawer.obj.bev_x || 0).toFixed(1) },
                    { label: "BEV Y", value: Number(drawer.obj.bev_y || 0).toFixed(1) },
                    { label: "Confidence", value: (Number(drawer.obj.confidence || 0) * 100).toFixed(0) + "%" }
                ] : []
                delegate: Row {
                    width: parent.width; spacing: 8
                    Text { text: modelData.label; color: Theme.textSecondary; font.pixelSize: Theme.fontSm; width: 80 }
                    Text { text: modelData.value; color: Theme.textPrimary; font.pixelSize: Theme.fontSm; font.bold: true }
                }
            }
        }

        Text { visible: drawer.obj === null; text: "No object selected"; color: Theme.textMuted; font.pixelSize: Theme.fontSm }
    }
}
