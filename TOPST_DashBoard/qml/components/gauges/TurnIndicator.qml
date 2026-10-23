import QtQuick 2.12

Item {
    property int direction: Qt.LeftArrow
    property bool on: false
    property bool flashing: false

    scale: direction === Qt.LeftArrow ? 1 : -1

    Timer {
        interval: 450
        running: parent.on
        repeat: true
        onTriggered: parent.flashing = !parent.flashing
    }

    function paintArrow(ctx) {
        ctx.beginPath()
        ctx.moveTo(0, height * 0.5)
        ctx.lineTo(width * 0.58, 0)
        ctx.lineTo(width * 0.58, height * 0.28)
        ctx.lineTo(width, height * 0.28)
        ctx.lineTo(width, height * 0.72)
        ctx.lineTo(width * 0.58, height * 0.72)
        ctx.lineTo(width * 0.58, height)
        ctx.closePath()
    }

    Canvas {
        anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            paintArrow(ctx)
            ctx.lineWidth = 1.5
            ctx.strokeStyle = "#3d5f79"
            ctx.stroke()
        }
    }

    Canvas {
        anchors.fill: parent
        visible: parent.on && parent.flashing
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            paintArrow(ctx)
            ctx.fillStyle = "#22c55e"
            ctx.shadowColor = "#22c55e"
            ctx.shadowBlur = 10
            ctx.fill()
        }
    }
}
