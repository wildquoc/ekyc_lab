import QtQuick
import Fkyc 1.0
import "../components"

Item {
    id: page
    property real unit: 1
    property real ox: 0
    property real oy: 0
    property Item blurSource: null

    readonly property real boxW: 460 * page.unit
    readonly property real boxX: page.ox + (Theme.cardX + (Theme.cardW - 460) / 2) * page.unit
    readonly property bool faceReady: bridge.fields.faceReady === "yes"

    Text {
        x: page.boxX
        y: page.oy + (Theme.cardY + 280) * page.unit
        width: page.boxW
        text: bridge.fields.username ? ("Welcome, " + bridge.fields.username) : "Welcome"
        color: "#ffffff"
        horizontalAlignment: Text.AlignHCenter
        font.family: "SF Pro Display"
        font.pixelSize: 48 * page.unit
        font.weight: Font.Bold
    }

    Text {
        x: page.boxX
        y: page.oy + (Theme.cardY + 360) * page.unit
        width: page.boxW
        text: page.faceReady ? "Your FaceID is ready" : "Register a new FaceID profile."
        color: "#ffffff"
        opacity: 0.72
        horizontalAlignment: Text.AlignHCenter
        font.family: "SF Pro Display"
        font.pixelSize: 20 * page.unit
        font.weight: Font.Medium
    }

    PillButton {
        x: page.boxX + (page.boxW - 320 * page.unit) / 2
        y: page.oy + (Theme.cardY + 440) * page.unit
        width: 320 * page.unit
        height: 72 * page.unit
        frosted: true
        blurSource: page.blurSource
        label: page.faceReady ? "Register again" : "Register"
        fadedSuffix: page.faceReady ? "" : "FaceID"
        labelSize: 26 * page.unit
        textFont: "SF Pro Display"
        onClicked: bridge.startRegister()
    }
}
