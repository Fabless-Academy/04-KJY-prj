import QtQuick 2.12
import QtQuick.Controls.Styles 1.4
import QtQuick.Extras 1.4

DashboardGaugeStyle {
    id: iconGaugeStyle
    minimumValueAngle: -60
    maximumValueAngle: 60
    tickmarkStepSize: 1
    labelStepSize: 1
    labelInset: toPixels(-0.25)
    minorTickmarkCount: 3
    needleLength: toPixels(0.82)
    needleBaseWidth: toPixels(0.08)
    needleTipWidth: toPixels(0.03)
    halfGauge: true

    property string icon: ""
    property color minWarningColor: "transparent"
    property color maxWarningColor: "transparent"
    property string lowLabel: "L"
    property string highLabel: "H"

    tickmark: Rectangle {
        implicitWidth: toPixels(0.045)
        implicitHeight: toPixels(0.16)
        radius: width / 2
        antialiasing: true
        color: "#e2e9ee"
    }

    minorTickmark: Rectangle {
        implicitWidth: toPixels(0.02)
        implicitHeight: toPixels(0.1)
        radius: width / 2
        antialiasing: true
        color: "#8394a1"
    }

    background: Item {
        Canvas {
            anchors.fill: parent

            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                paintBackground(ctx)

                if (minWarningColor !== "transparent") {
                    ctx.beginPath()
                    ctx.lineWidth = iconGaugeStyle.toPixels(0.08)
                    ctx.strokeStyle = minWarningColor
                    ctx.arc(outerRadius,
                            outerRadius,
                            outerRadius - tickmarkInset - ctx.lineWidth / 2,
                            degToRad(minimumValueAngle - 90),
                            degToRad(minimumValueAngle - 55),
                            false)
                    ctx.stroke()
                }

                if (maxWarningColor !== "transparent") {
                    ctx.beginPath()
                    ctx.lineWidth = iconGaugeStyle.toPixels(0.08)
                    ctx.strokeStyle = maxWarningColor
                    ctx.arc(outerRadius,
                            outerRadius,
                            outerRadius - tickmarkInset - ctx.lineWidth / 2,
                            degToRad(maximumValueAngle - 25),
                            degToRad(maximumValueAngle - 90),
                            true)
                    ctx.stroke()
                }
            }
        }

        Image {
            source: icon
            anchors.bottom: parent.verticalCenter
            anchors.bottomMargin: toPixels(0.28)
            anchors.horizontalCenter: parent.horizontalCenter
            width: toPixels(0.28)
            height: width
            fillMode: Image.PreserveAspectFit
        }
    }

    tickmarkLabel: Text {
        color: "#e8eef2"
        visible: styleData.value === 0 || styleData.value === 1
        font.pixelSize: iconGaugeStyle.toPixels(0.16)
        text: styleData.value === 0 ? iconGaugeStyle.lowLabel : iconGaugeStyle.highLabel
    }
}
