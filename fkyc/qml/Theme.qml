pragma Singleton
import QtQuick

QtObject {
    readonly property color canvas: "#ffffff"
    readonly property color ink: "#ffffff"
    readonly property color inkOnLight: "#111111"
    readonly property color muted: "#6b7280"
    readonly property color glass: Qt.rgba(1, 1, 1, 0.22)
    readonly property color glassEdge: Qt.rgba(0.851, 0.851, 0.851, 0.35)
    readonly property color cameraWell: "#000000"
    readonly property color card: "#ffffff"
    readonly property color pill: Qt.rgba(1, 1, 1, 0.38)
    readonly property color pillEdge: Qt.rgba(1, 1, 1, 0.50)
    readonly property color glowAmber: "#ff9a1f"
    readonly property color glowCore: "#ffd27a"
    readonly property color ok: "#10b981"
    readonly property color warn: "#f59e0b"
    readonly property color bad: "#ef4444"
    readonly property color info: "#0284c7"

    readonly property int fontDisplay: 72
    readonly property int fontBrand: 14
    readonly property int fontButton: 18
    readonly property int fontOr: 14
    readonly property int fontCameraLabel: 18
    readonly property int fontSection: 16
    readonly property int fontBody: 15
    readonly property int fontCaption: 12

    readonly property int frameW: 1440
    readonly property int frameH: 1024
    readonly property int cardX: 109
    readonly property int cardY: 75
    readonly property int cardW: 1220
    readonly property int cardH: 872
    readonly property int faceCamW: 480
    readonly property int faceCamH: 600
    readonly property int loginPhotoW: 528
    readonly property int loginPhotoH: 400
    readonly property color processCurrent: "#9b1c1c"
    readonly property color processIdle: "#fad4d8"
    readonly property color processLine: "#111111"
    readonly property int radiusGlass: 85
    readonly property int radiusCamera: 56
    readonly property int radiusPhoto: 52
    readonly property int radiusCard: 28
    readonly property int loginCardRadius: 48
    readonly property int radiusPill: 999
    readonly property int spaceTitle: 119
    readonly property int blurGlass: 24
    readonly property int blurButton: 18
    readonly property int glowBlur: 28
    readonly property int glowSpreadHover: 8
    readonly property int glowSpreadPressed: 14

    readonly property string fontFamily: "SF Pro Display"
}
