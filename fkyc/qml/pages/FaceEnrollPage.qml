import QtQuick
import Fkyc 1.0
import "../components"

Item {
    id: page
    property real unit: 1
    property real ox: 0
    property real oy: 0
    property Item blurSource: null

    readonly property int authPercent: {
        var s = bridge.stage
        var p = bridge.progress
        var idx = 0
        if (s === "face_quality")
            idx = 1
        else if (s === "turn_left" || s === "turn_right" || s === "recenter")
            idx = 2
        else if (s === "zoom_in" || s === "flashing")
            idx = 3
        else if (s === "capture" || s === "failed")
            idx = 4
        var pct = Math.round((idx + Math.min(1, Math.max(0, p))) / 5 * 100)
        return Math.max(2, Math.min(100, pct))
    }

    GuideList {
        unit: page.unit
        x: page.ox + (Theme.cardX + 28) * page.unit
        y: page.oy + (Theme.cardY + 120) * page.unit
        width: 250 * page.unit
    }

    InstructionPanel {
        unit: page.unit
        x: page.ox + (Theme.cardX + Theme.cardW - 278) * page.unit
        y: page.oy + (Theme.cardY + 120) * page.unit
        width: 250 * page.unit
    }

    Column {
        anchors.horizontalCenter: parent.left
        anchors.horizontalCenterOffset: page.ox + (Theme.cardX + Theme.cardW / 2) * page.unit
        y: page.oy + (Theme.cardY + 48 + Theme.faceCamH + 20) * page.unit
        spacing: 14 * page.unit
        width: 340 * page.unit

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Auth progress — " + page.authPercent + "%"
            color: Theme.ink
            font.family: Theme.fontFamily
            font.pixelSize: 20 * page.unit
            font.weight: Font.DemiBold
            style: Text.Raised
            styleColor: "#33000000"
        }

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 280 * page.unit
            height: 6 * page.unit
            radius: 3 * page.unit
            color: Qt.rgba(1, 1, 1, 0.35)

            Rectangle {
                width: Math.max(8 * page.unit, parent.width * page.authPercent / 100)
                height: parent.height
                radius: parent.radius
                color: "#f97316"
            }
        }

        PillButton {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 168 * page.unit
            height: 44 * page.unit
            label: "Restart"
            labelSize: 16 * page.unit
            onClicked: bridge.redo()
        }
    }
}
