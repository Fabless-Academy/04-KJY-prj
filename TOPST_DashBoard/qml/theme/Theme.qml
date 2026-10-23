pragma Singleton
import QtQuick 2.12

QtObject {
    readonly property color bgPrimary:   "#0b1118"
    readonly property color bgSecondary: "#101820"
    readonly property color bgPanel:     "#111922"
    readonly property color bgCard:      "#182531"
    readonly property color bgElevated:  "#1e2e3c"
    readonly property color bgScene:     "#15202a"

    readonly property color borderDefault: "#20303c"
    readonly property color borderActive:  "#59c0cd"
    readonly property color borderSubtle:  "#152028"

    readonly property color textPrimary:   "#f0f6fb"
    readonly property color textSecondary: "#8ea0af"
    readonly property color textMuted:     "#5a6a78"
    readonly property color textAccent:    "#59c0cd"
    readonly property color textValue:     "#7ec3ff"

    readonly property color accentCyan:    "#59c0cd"
    readonly property color accentBlue:    "#3a8aff"
    readonly property color statusGreen:   "#22c55e"
    readonly property color statusOrange:  "#f59e0b"
    readonly property color statusRed:     "#ef4444"

    readonly property color gradPanelTop:    "#161e28"
    readonly property color gradPanelMid:    "#111820"
    readonly property color gradPanelBottom: "#0c1218"
    readonly property color gradCardTop:     "#1e2e3c"
    readonly property color gradCardBottom:  "#142028"

    readonly property int spacingXs:  4
    readonly property int spacingSm:  8
    readonly property int spacingMd:  12
    readonly property int spacingLg:  16
    readonly property int spacingXl:  24
    readonly property int spacing2xl: 32

    readonly property int radiusSm:   8
    readonly property int radiusMd:   14
    readonly property int radiusLg:   18
    readonly property int radiusXl:   24
    readonly property int radiusFull: 999

    readonly property int fontXs:    9
    readonly property int fontSm:    11
    readonly property int fontMd:    13
    readonly property int fontLg:    16
    readonly property int fontXl:    20
    readonly property int fontTitle: 24
    readonly property int fontHero:  32

    function rgba(hex, alpha) {
        var r = parseInt(hex.substring(1, 3), 16) / 255
        var g = parseInt(hex.substring(3, 5), 16) / 255
        var b = parseInt(hex.substring(5, 7), 16) / 255
        return Qt.rgba(r, g, b, alpha)
    }
}
