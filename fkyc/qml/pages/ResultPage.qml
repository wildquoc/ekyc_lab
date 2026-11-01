import QtQuick
import QtQuick.Layouts
import Fkyc 1.0
import "../components"

Item {
    id: page
    property real unit: 1
    property real ox: 0
    property real oy: 0
    property Item blurSource: null
    readonly property bool loginResult: bridge.screen === "loginResult"
    readonly property bool faceResult: bridge.screen === "faceResult"
    readonly property bool infoResult: page.loginResult || page.faceResult
    readonly property bool citizenResult: bridge.screen === "citizenResult"
    readonly property bool studentResult: bridge.screen === "studentResult"
    readonly property bool glassResult: page.citizenResult || page.studentResult

    function formatLoginName(name) {
        var raw = (name || "").trim()
        if (raw === "")
            return "—"
        var parts = raw.split(/\s+/).filter(function (w) { return w.length > 0 })
        if (parts.length <= 3)
            return parts.join(" ")
        var mid = Math.ceil(parts.length / 2)
        return parts.slice(0, mid).join(" ") + "\n" + parts.slice(mid).join(" ")
    }

    function formatGender(gender) {
        var raw = (gender || "").trim()
        if (raw === "")
            return ""
        var fold = raw.toLowerCase().replace(/ữ/g, "u").replace(/ú/g, "u")
        if (fold === "nam" || fold === "male" || fold === "m")
            return "Male"
        if (fold === "nu" || fold === "nữ" || fold === "female" || fold === "f")
            return "Female"
        return raw
    }

    function rowsFor(screen, fields) {
        var idRow = { caption: "Citizen ID", value: fields.citizenId || "" }
        var nameRow = { caption: "Name", value: fields.fullName || "" }
        var genderRow = { caption: "Gender", value: formatGender(fields.gender) }
        var dobRow = { caption: "Date of Birth", value: fields.dob || "" }
        var studentRow = { caption: "Student ID", value: fields.studentId || "" }
        if (screen === "loginResult" || screen === "faceResult")
            return [idRow, genderRow, dobRow]
        if (screen === "studentResult")
            return [studentRow, nameRow]
        return [idRow, nameRow, genderRow, dobRow]
    }

    function glassRows(screen, fields) {
        if (screen === "studentResult")
            return [
                { caption: "Student ID", value: fields.studentId || "", lines: 1 },
                { caption: "Name", value: formatLoginName(fields.fullName), lines: 2 }
            ]
        return [
            { caption: "Citizen ID", value: fields.citizenId || "", lines: 1 },
            { caption: "Name", value: formatLoginName(fields.fullName), lines: 2 },
            { caption: "Gender", value: formatGender(fields.gender), lines: 1 },
            { caption: "Date of Birth", value: fields.dob || "", lines: 1 }
        ]
    }

    Column {
        visible: page.infoResult
        x: page.ox + (Theme.cardX + 48) * page.unit
        y: page.oy + (Theme.cardY + 36 + Theme.loginPhotoH + 24) * page.unit
        width: Theme.loginPhotoW * page.unit
        spacing: 22 * page.unit

        Column {
            spacing: 2 * page.unit
            width: parent.width
            Text {
                text: "Student ID"
                color: Qt.rgba(1, 1, 1, 0.82)
                font.family: "SF Pro Display"
                font.pixelSize: 39 * page.unit
                font.weight: Font.DemiBold
            }
            Text {
                text: bridge.fields.studentId || "—"
                color: "#ffffff"
                font.family: "SF Pro Display"
                font.pixelSize: 84 * page.unit
                font.weight: Font.Bold
                width: parent.width
                wrapMode: Text.NoWrap
                elide: Text.ElideNone
                fontSizeMode: Text.HorizontalFit
                minimumPixelSize: 36 * page.unit
            }
        }

        Column {
            spacing: 2 * page.unit
            width: parent.width
            Text {
                text: "Name"
                color: Qt.rgba(1, 1, 1, 0.82)
                font.family: "SF Pro Display"
                font.pixelSize: 39 * page.unit
                font.weight: Font.DemiBold
            }
            Text {
                text: formatLoginName(bridge.fields.fullName)
                color: "#ffffff"
                font.family: "SF Pro Display"
                font.pixelSize: 66 * page.unit
                font.weight: Font.Bold
                width: parent.width
                wrapMode: Text.NoWrap
                maximumLineCount: 2
                elide: Text.ElideNone
                fontSizeMode: Text.HorizontalFit
                minimumPixelSize: 32 * page.unit
            }
        }
    }

    Item {
        id: citizenFields
        visible: page.glassResult
        x: page.ox + (Theme.cardX + 36 + Theme.loginPhotoW + 48) * page.unit
        y: page.oy + (Theme.cardY + 28) * page.unit
        width: (Theme.cardW - 36 - Theme.loginPhotoW - 48 - 56) * page.unit
        height: (Theme.cardH - 56) * page.unit

        ColumnLayout {
            anchors.fill: parent
            spacing: 0
            Repeater {
                model: page.glassResult ? page.glassRows(bridge.screen, bridge.fields) : []
                delegate: FieldRow {
                    required property var modelData
                    caption: modelData.caption
                    value: modelData.value
                    maxLines: modelData.lines
                    captionSize: 33 * page.unit
                    valueSize: 58 * page.unit
                    captionWeight: Font.DemiBold
                    captionColor: Qt.rgba(1, 1, 1, 0.82)
                    valueColor: "#ffffff"
                    expand: true
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                }
            }
            Text {
                visible: bridge.errorText !== ""
                text: bridge.errorText
                color: Theme.bad
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                font.family: Theme.fontFamily
                font.pixelSize: 22 * page.unit
            }
        }
    }

    ResultCard {
        visible: !page.glassResult
        x: ox + (Theme.cardX + Theme.cardW * 0.50 + 24) * unit
        y: oy + (Theme.cardY + 36) * unit
        width: (Theme.cardW * 0.50 - 72) * unit
        height: page.infoResult ? 540 * unit : (Theme.cardH - 72) * unit
        rows: rowsFor(bridge.screen, bridge.fields)
        showActions: !page.infoResult
        distributeRows: page.infoResult
        cornerRadius: page.infoResult ? Theme.loginCardRadius * unit : Theme.radiusCard
        captionSize: page.infoResult ? 36 * unit : 0
        valueSize: page.infoResult ? 54 * unit : 0
        contentMargins: page.infoResult ? 40 * unit : 28
        contentSpacing: page.infoResult ? 32 * unit : 16
        onConfirm: bridge.confirm()
        onRedo: bridge.redo()
    }

    Column {
        visible: page.infoResult
        x: page.ox + (Theme.cardX + Theme.cardW - 56 - 260) * page.unit
        y: page.oy + (Theme.cardY + Theme.cardH - 56 - 72 - 18 - 80) * page.unit
        spacing: 18 * page.unit
        width: 260 * page.unit

        PillButton {
            width: parent.width
            height: 80 * page.unit
            frosted: true
            blurSource: page.blurSource
            label: "Confirm"
            labelSize: 39 * page.unit
            textFont: "SF Pro Display"
            onClicked: bridge.confirm()
        }
        PillButton {
            width: 210 * page.unit
            height: 72 * page.unit
            anchors.right: parent.right
            frosted: true
            blurSource: page.blurSource
            label: "Redo"
            labelSize: 36 * page.unit
            textFont: "SF Pro Display"
            onClicked: bridge.redo()
        }
    }

    Column {
        visible: page.glassResult
        x: page.ox + (Theme.cardX + 36 + Theme.loginPhotoW - 260 - 8) * page.unit
        y: page.oy + (Theme.cardY + 36 + Theme.loginPhotoH + 32) * page.unit
        spacing: 16 * page.unit
        width: 260 * page.unit

        PillButton {
            width: parent.width
            height: 80 * page.unit
            frosted: true
            blurSource: page.blurSource
            label: "Confirm"
            labelSize: 39 * page.unit
            textFont: "SF Pro Display"
            enabled: !bridge.busy
            opacity: enabled ? 1 : 0.45
            onClicked: if (enabled) bridge.confirm()
        }
        PillButton {
            width: 210 * page.unit
            height: 72 * page.unit
            anchors.horizontalCenter: parent.horizontalCenter
            frosted: true
            blurSource: page.blurSource
            label: "Redo"
            labelSize: 36 * page.unit
            textFont: "SF Pro Display"
            onClicked: bridge.redo()
        }
    }
}
