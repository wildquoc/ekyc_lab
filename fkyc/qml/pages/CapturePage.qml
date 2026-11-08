import QtQuick
import Fkyc 1.0

Item {
    property real unit: 1
    property real ox: 0
    property real oy: 0
    property Item blurSource: null
    enabled: false

    Text {
        visible: bridge.screen === "login"
        anchors.horizontalCenter: parent.left
        anchors.horizontalCenterOffset: ox + (Theme.cardX + Theme.cardW / 2) * unit
        y: oy + (Theme.cardY + 48 + Theme.loginCamDrop + Theme.faceCamH + 24) * unit
        text: "Login with FaceID"
        color: Theme.ink
        font.family: "SF Pro Display"
        font.pixelSize: 28 * unit
        font.weight: Font.Bold
        style: Text.Raised
        styleColor: "#33000000"
        enabled: false
    }
}
