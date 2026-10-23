import QtQuick 2.12
import "../theme"

Rectangle {
    id: dialog

    property bool open: false
    property string currentScenario: "Default Scenario"
    property var scenarios: []

    signal closed()
    signal scenarioSelected(string name)

    anchors.fill: parent
    visible: open
    color: "#66000000"

    MouseArea {
        anchors.fill: parent
        // 바깥 영역 클릭 시 다이얼로그를 닫는다.
        onClicked: dialog.closed()
    }

    Rectangle {
        width: 360
        height: Math.min(440, 80 + scenarioListView.contentHeight)
        anchors.centerIn: parent
        radius: 14
        color: "#141c26"
        border.color: Theme.borderDefault
        border.width: 1

        Column {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12

            Text {
                text: "Scenario Selection"
                color: Theme.textPrimary
                font.pixelSize: Theme.fontLg
                font.bold: true
            }

            Text {
                text: "Current: " + dialog.currentScenario
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSm
            }

            Rectangle {
                width: parent.width
                height: parent.height - 78
                radius: 10
                color: "#0e151c"
                border.color: Theme.borderDefault
                border.width: 1

                ListView {
                    id: scenarioListView
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 6
                    clip: true
                    model: dialog.scenarios

                    delegate: Rectangle {
                        // 현재 선택된 시나리오는 강조하고, 클릭 시 scenarioSelected signal을 보낸다.
                        width: scenarioListView.width
                        height: 36
                        radius: 8
                        color: modelData === dialog.currentScenario ? Theme.rgba("#59c0cd", 0.15) : "transparent"
                        border.color: modelData === dialog.currentScenario ? Theme.accentCyan : Theme.borderDefault
                        border.width: 1

                        Text {
                            anchors.left: parent.left
                            anchors.leftMargin: 12
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData
                            color: modelData === dialog.currentScenario ? Theme.accentCyan : Theme.textPrimary
                            font.pixelSize: Theme.fontSm
                            font.bold: modelData === dialog.currentScenario
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: dialog.scenarioSelected(modelData)
                        }
                    }
                }
            }
        }
    }
}
