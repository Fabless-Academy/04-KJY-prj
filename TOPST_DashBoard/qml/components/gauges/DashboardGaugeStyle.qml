import QtQuick 2.12
import QtQuick.Controls.Styles 1.4

CircularGaugeStyle {
    tickmarkInset: toPixels(0.04)
    minorTickmarkInset: tickmarkInset
    labelStepSize: 20
    labelInset: toPixels(0.23)

    property real xCenter: outerRadius
    property real yCenter: outerRadius
    property real needleLength: outerRadius - tickmarkInset * 1.15
    property real needleTipWidth: toPixels(0.02)
    property real needleBaseWidth: toPixels(0.06)
    property bool halfGauge: false

    function toPixels(percentage) {
        return percentage * outerRadius
    }

    function degToRad(degrees) {
        return degrees * (Math.PI / 180)
    }

    function paintBackground(ctx) {
        if (halfGauge) {
            ctx.beginPath()
            ctx.rect(0, 0, ctx.canvas.width, ctx.canvas.height / 2)
            ctx.clip()
        }

        ctx.beginPath()
        var outerGradient = ctx.createRadialGradient(xCenter, yCenter, 0, xCenter, yCenter, outerRadius * 1.05)
        outerGradient.addColorStop(0.0, "#2e4050")
        outerGradient.addColorStop(0.3, "#1e2c38")
        outerGradient.addColorStop(0.58, "#11181f")
        outerGradient.addColorStop(0.82, "#0c1016")
        outerGradient.addColorStop(1.0, "#080b0e")
        ctx.fillStyle = outerGradient
        ctx.arc(xCenter, yCenter, outerRadius, 0, Math.PI * 2)
        ctx.fill()

        ctx.beginPath()
        ctx.lineWidth = toPixels(0.025)
        var rimGrad = ctx.createLinearGradient(0, 0, 0, outerRadius * 2)
        rimGrad.addColorStop(0.0, "#6a8498")
        rimGrad.addColorStop(0.35, "#4a6878")
        rimGrad.addColorStop(0.65, "#384e5e")
        rimGrad.addColorStop(1.0, "#283a48")
        ctx.strokeStyle = rimGrad
        ctx.arc(xCenter, yCenter, outerRadius - ctx.lineWidth / 2, 0, Math.PI * 2)
        ctx.stroke()

        ctx.beginPath()
        ctx.lineWidth = toPixels(0.005)
        ctx.strokeStyle = "rgba(160,210,240,0.15)"
        ctx.arc(xCenter, yCenter, outerRadius - toPixels(0.035), degToRad(-140), degToRad(-10), false)
        ctx.stroke()

        ctx.beginPath()
        var glow = ctx.createRadialGradient(xCenter, yCenter, outerRadius * 0.12, xCenter, yCenter, outerRadius)
        glow.addColorStop(0.0, "rgba(140,209,255,0.14)")
        glow.addColorStop(0.5, "rgba(140,209,255,0.03)")
        glow.addColorStop(1.0, "rgba(0,0,0,0)")
        ctx.fillStyle = glow
        ctx.arc(xCenter, yCenter, outerRadius - tickmarkInset, 0, Math.PI * 2)
        ctx.fill()

        ctx.beginPath()
        var topHL = ctx.createLinearGradient(xCenter, 0, xCenter, outerRadius * 0.6)
        topHL.addColorStop(0.0, "rgba(200,230,255,0.06)")
        topHL.addColorStop(1.0, "rgba(0,0,0,0)")
        ctx.fillStyle = topHL
        ctx.arc(xCenter, yCenter, outerRadius * 0.92, 0, Math.PI * 2)
        ctx.fill()
    }

    background: Canvas {
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            paintBackground(ctx)
        }

        Text {
            id: speedText
            font.pixelSize: toPixels(0.28)
            text: Math.round(control.value)
            color: "#f5f7f9"
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.verticalCenter
            anchors.topMargin: toPixels(0.08)
        }

        Text {
            text: "km/h"
            color: "#9db0bf"
            font.pixelSize: toPixels(0.085)
            anchors.top: speedText.bottom
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }

    tickmark: Rectangle {
        implicitWidth: toPixels(0.012)
        implicitHeight: toPixels(styleData.value % 20 === 0 ? 0.11 : 0.06)
        radius: width / 2
        antialiasing: true
        color: styleData.value >= 220 ? "#b8cad6" : "#dce4ea"
    }

    minorTickmark: Rectangle {
        implicitWidth: toPixels(0.007)
        implicitHeight: toPixels(0.035)
        radius: width / 2
        antialiasing: true
        color: "#768896"
    }

    tickmarkLabel: Text {
        font.pixelSize: Math.max(8, toPixels(0.1))
        text: styleData.value
        color: styleData.value >= 220 ? "#bac8d2" : "#e7edf1"
        antialiasing: true
    }

    needle: Canvas {
        implicitWidth: needleBaseWidth
        implicitHeight: needleLength

        property real xCenter: width / 2

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()

            ctx.beginPath()
            ctx.moveTo(xCenter, height)
            ctx.lineTo(xCenter - needleBaseWidth / 2, height - needleBaseWidth / 2)
            ctx.lineTo(xCenter - needleTipWidth / 2, 0)
            ctx.lineTo(xCenter, 0)
            ctx.closePath()
            var ng = ctx.createLinearGradient(0, 0, 0, height)
            ng.addColorStop(0.0, "#a0e0ff")
            ng.addColorStop(0.5, "#70c8f0")
            ng.addColorStop(1.0, "#4aa0d0")
            ctx.fillStyle = ng
            ctx.fill()

            ctx.beginPath()
            ctx.moveTo(xCenter, 0)
            ctx.lineTo(xCenter + needleTipWidth / 2, 0)
            ctx.lineTo(xCenter + needleBaseWidth / 2, height - needleBaseWidth / 2)
            ctx.lineTo(xCenter, height)
            ctx.closePath()
            ctx.fillStyle = "rgba(80,170,220,0.5)"
            ctx.fill()

            ctx.beginPath()
            ctx.arc(xCenter, height - toPixels(0.03), toPixels(0.05), 0, Math.PI * 2)
            var pg = ctx.createRadialGradient(xCenter, height - toPixels(0.03), 0, xCenter, height - toPixels(0.03), toPixels(0.05))
            pg.addColorStop(0.0, "#e8f0f6")
            pg.addColorStop(0.5, "#c0d0de")
            pg.addColorStop(1.0, "#8898a8")
            ctx.fillStyle = pg
            ctx.fill()
        }
    }

    foreground: null
}
