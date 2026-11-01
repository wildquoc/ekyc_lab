import QtQuick
import Fkyc 1.0
import "../components"

Item {
    id: page
    property real unit: 1
    property real ox: 0
    property real oy: 0
    property Item blurSource: null

    readonly property bool alert: bridge.errorText !== ""
    readonly property color statusColor: {
        if (bridge.ovalColor === "red")
            return Theme.bad
        if (bridge.ovalColor === "yellow")
            return Theme.warn
        return Theme.ok
    }

    Text {
        anchors.horizontalCenter: parent.left
        anchors.horizontalCenterOffset: page.ox + (Theme.cardX + Theme.cardW / 2) * page.unit
        y: page.oy + (Theme.cardY + 48 + Theme.faceCamH + 22) * page.unit
        text: "Exam monitor"
        color: Theme.ink
        font.family: "SF Pro Display"
        font.pixelSize: 28 * page.unit
        font.weight: Font.Bold
        style: Text.Raised
        styleColor: "#33000000"
    }

    Column {
        x: page.ox + (Theme.cardX + 36) * page.unit
        y: page.oy + (Theme.cardY + 48) * page.unit
        width: 250 * page.unit
        spacing: 18 * page.unit

        Text {
            text: "Student"
            color: Qt.rgba(1, 1, 1, 0.72)
            font.family: "SF Pro Display"
            font.pixelSize: 18 * page.unit
            font.weight: Font.DemiBold
        }
        Text {
            width: parent.width
            text: bridge.fields.fullName || "—"
            color: "#ffffff"
            font.family: "SF Pro Display"
            font.pixelSize: 26 * page.unit
            font.weight: Font.Bold
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            text: (bridge.fields.studentId ? ("ID  " + bridge.fields.studentId) : "")
            visible: text !== ""
            color: Qt.rgba(1, 1, 1, 0.82)
            font.family: "SF Pro Display"
            font.pixelSize: 18 * page.unit
        }
    }

    Column {
        x: page.ox + (Theme.cardX + Theme.cardW - 36 - 280) * page.unit
        y: page.oy + (Theme.cardY + 48) * page.unit
        width: 280 * page.unit
        spacing: 16 * page.unit

        Rectangle {
            width: parent.width
            height: 52 * page.unit
            radius: 26 * page.unit
            color: Qt.rgba(page.statusColor.r, page.statusColor.g, page.statusColor.b, 0.28)
            border.color: page.statusColor
            border.width: 1
            Text {
                anchors.centerIn: parent
                text: page.alert ? "Alert" : "Monitoring"
                color: "#ffffff"
                font.family: "SF Pro Display"
                font.pixelSize: 22 * page.unit
                font.weight: Font.Bold
            }
        }

        Text {
            width: parent.width
            text: page.alert ? bridge.errorText : (bridge.prompt || "Looking at the screen.")
            color: page.alert ? "#fecaca" : "#ffffff"
            font.family: "SF Pro Display"
            font.pixelSize: 24 * page.unit
            font.weight: Font.DemiBold
            wrapMode: Text.WordWrap
            style: Text.Raised
            styleColor: "#66000000"
        }
    }

    PillButton {
        anchors.horizontalCenter: parent.left
        anchors.horizontalCenterOffset: page.ox + (Theme.cardX + Theme.cardW / 2) * page.unit
        y: page.oy + (Theme.cardY + Theme.cardH - 56 - 56) * page.unit
        width: 220 * page.unit
        height: 56 * page.unit
        frosted: true
        blurSource: page.blurSource
        label: "End exam"
        labelSize: 22 * page.unit
        textFont: "SF Pro Display"
        onClicked: bridge.goHome()
    }
}
