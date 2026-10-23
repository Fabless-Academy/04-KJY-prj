import QtQuick 2.12
import QtQuick.Controls.Styles 1.4
import QtQuick.Extras 1.4

DashboardGaugeStyle {
    id: tachometerStyle
    property real rpmValue: 0

    tickmarkStepSize: 1
    labelStepSize: 1
    needleLength: toPixels(0.82)
    needleBaseWidth: toPixels(0.08)
    needleTipWidth: toPixels(0.03)

    tickmark: Rectangle {
        implicitWidth: toPixels(0.028)
        implicitHeight: toPixels(0.085)
        radius: width / 2
        antialiasing: true
        color: styleData.index >= 7 ? "#cad4dc" : "#dfe6eb"
    }

    minorTickmark: null

    tickmarkLabel: Text {
        font.pixelSize: Math.max(7, toPixels(0.11))
        text: styleData.value
        color: styleData.index >= 7 ? "#c9d4db" : "#e7edf1"
        antialiasing: true
    }

    background: Canvas {
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            paintBackground(ctx)

            ctx.beginPath()
            ctx.lineWidth = tachometerStyle.toPixels(0.06)
            var rz = ctx.createLinearGradient(
                outerRadius + outerRadius * Math.cos(degToRad(36 - 90)),
                outerRadius + outerRadius * Math.sin(degToRad(36 - 90)),
                outerRadius + outerRadius * Math.cos(degToRad(84 - 90)),
                outerRadius + outerRadius * Math.sin(degToRad(84 - 90))
            )
            rz.addColorStop(0.0, "#f0a060")
            rz.addColorStop(0.4, "#e07040")
            rz.addColorStop(1.0, "#c04030")
            ctx.strokeStyle = rz
            ctx.arc(outerRadius,
                    outerRadius,
                    outerRadius - tickmarkInset - ctx.lineWidth / 2,
                    degToRad(36),
                    degToRad(84),
                    false)
            ctx.stroke()
        }

        Text {
            id: rpmText
            font.pixelSize: tachometerStyle.toPixels(0.24)
            text: Math.round(tachometerStyle.rpmValue)
            color: "#f5f7f9"
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.verticalCenter
            anchors.topMargin: 16
        }

        Text {
            text: "rpm"
            color: "#9db0bf"
            font.pixelSize: tachometerStyle.toPixels(0.085)
            anchors.top: rpmText.bottom
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }
}
