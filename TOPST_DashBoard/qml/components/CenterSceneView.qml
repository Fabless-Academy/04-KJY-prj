import QtQuick 2.12
import "../theme"
import "scene"

Item {
    id: view
    property real recommendedSpeedKmh: -1
    property string proximityStatus: "unavailable"

    // 중앙 패널은 3D scene과 그 주변 HUD 카드들을 감싸는 컨테이너 역할을 한다.
    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusXl
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0e1620" }
            GradientStop { position: 0.3; color: "#0a1018" }
            GradientStop { position: 1.0; color: "#060c14" }
        }
        border.color: "#1a2e3c"
        border.width: 1
    }

    Rectangle {
        anchors.top: parent.top
        anchors.topMargin: 1
        anchors.left: parent.left
        anchors.leftMargin: 12
        anchors.right: parent.right
        anchors.rightMargin: 12
        height: 1
        radius: 1
        color: Theme.rgba("#ffffff", 0.05)
    }

    Text {
        x: 24; y: 18; z: 10
        text: "Zonal Education Kit DashBoard"
        color: Theme.textPrimary
        font.pixelSize: Theme.fontTitle + 22
        font.bold: true
    }

    Item {
        id: sceneContainer
        x: 16; y: 86
        width: parent.width - 32
        height: parent.height - 158
        clip: true

        Rectangle {
            anchors.fill: parent
            radius: Theme.radiusLg
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#0a1424" }
                GradientStop { position: 0.35; color: "#0c1828" }
                GradientStop { position: 0.65; color: "#081220" }
                GradientStop { position: 1.0; color: "#040a14" }
            }
            border.color: Theme.borderSubtle
        }

        ObjectScene {
            id: scene3d
            anchors.fill: parent
            anchors.margins: 6
            z: 1
            // 실제 lane/object/path 렌더링은 ObjectScene이 담당하고, 이 컨테이너는 입력만 전달한다.
            bevObjects: app.overlayObject ? root.bevObjects : []
            lanePolylines: app.overlayLane ? root.lanePolylines : [[], [], [], []]
            laneModel: root.laneModel
            laneFrameWidth: root.laneFrameWidth
            laneFrameHeight: root.laneFrameHeight
            showPath: app.overlayPath
        }

        Canvas {
            anchors.fill: parent
            z: 5
            onPaint: {
                // 화면 가장자리와 horizon glow를 덧씌워 scene 깊이감을 보정한다.
                var ctx = getContext("2d")
                ctx.reset()
                var w = width, h = height, r = Theme.radiusLg

                ctx.beginPath()
                ctx.roundedRect(0, 0, w, h, r, r)
                ctx.clip()

                var top = ctx.createLinearGradient(0, 0, 0, 50)
                top.addColorStop(0, "rgba(6,12,20,0.7)")
                top.addColorStop(1, "transparent")
                ctx.fillStyle = top
                ctx.fillRect(0, 0, w, 50)

                var bot = ctx.createLinearGradient(0, h - 50, 0, h)
                bot.addColorStop(0, "transparent")
                bot.addColorStop(1, "rgba(4,8,16,0.6)")
                ctx.fillStyle = bot
                ctx.fillRect(0, h - 50, w, 50)

                var lft = ctx.createLinearGradient(0, 0, 30, 0)
                lft.addColorStop(0, "rgba(6,12,20,0.5)")
                lft.addColorStop(1, "transparent")
                ctx.fillStyle = lft
                ctx.fillRect(0, 0, 30, h)

                var rgt = ctx.createLinearGradient(w - 30, 0, w, 0)
                rgt.addColorStop(0, "transparent")
                rgt.addColorStop(1, "rgba(6,12,20,0.5)")
                ctx.fillStyle = rgt
                ctx.fillRect(w - 30, 0, 30, h)

                var horizonY = h * 0.32
                var hGlow = ctx.createLinearGradient(0, horizonY - 40, 0, horizonY + 40)
                hGlow.addColorStop(0, "transparent")
                hGlow.addColorStop(0.25, "rgba(80,120,170,0.08)")
                hGlow.addColorStop(0.45, "rgba(100,145,200,0.2)")
                hGlow.addColorStop(0.5, "rgba(120,165,220,0.28)")
                hGlow.addColorStop(0.55, "rgba(100,145,200,0.2)")
                hGlow.addColorStop(0.75, "rgba(80,120,170,0.08)")
                hGlow.addColorStop(1, "transparent")
                ctx.fillStyle = hGlow
                ctx.fillRect(0, horizonY - 40, w, 80)
            }
        }
    }

    Row {
        x: 24
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 16
        spacing: 12

        Repeater {
            // 하단 HUD는 객체 수, 최전방 객체, lane별 객체 분포를 빠르게 요약한다.
            model: [
                { label: "Objects", value: String(root.bevObjects.length) },
                { label: "Closest", value: root.closestObject() ? ("ID " + String(root.closestObject().track_id || "-")) : "-" },
                { label: "Left/Ego/Right", value: root.countObjectsInLane(0) + " / " + root.countObjectsInLane(1) + " / " + root.countObjectsInLane(2) },
                { label: "Distance-based target", value: view.recommendedSpeedKmh < 0 ? "n/a" : Number(view.recommendedSpeedKmh).toFixed(0) + " km/h (" + view.proximityStatus + ")" }
            ]
            delegate: Rectangle {
                width: 190; height: 50
                radius: Theme.radiusMd
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#192838" }
                    GradientStop { position: 1.0; color: "#0e1a24" }
                }
                border.color: "#223243"
                Rectangle {
                    anchors.top: parent.top
                    anchors.topMargin: 1
                    anchors.left: parent.left
                    anchors.leftMargin: 5
                    anchors.right: parent.right
                    anchors.rightMargin: 5
                    height: 1; radius: 1
                    color: Theme.rgba("#ffffff", 0.03)
                }
                Column {
                    anchors.centerIn: parent
                    spacing: 0
                    Text {
                        text: modelData.label
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSm
                        font.bold: true
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                    Text {
                        text: modelData.value
                        color: Theme.textValue
                        font.pixelSize: Theme.fontMd
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: if (index === 1 && root.closestObject()) app.selectObject(0)
                }
            }
        }
    }
}
