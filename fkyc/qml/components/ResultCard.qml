import QtQuick
import QtQuick.Layouts
import Fkyc 1.0

Rectangle {
    id: card
    property var rows: []
    property bool showActions: true
    property bool distributeRows: false
    property real cornerRadius: Theme.radiusCard
    property real captionSize: 0
    property real valueSize: 0
    property real contentMargins: 28
    property real contentSpacing: 16
    signal confirm()
    signal redo()
    color: Theme.card
    radius: cornerRadius
    implicitWidth: 460

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: card.contentMargins
        spacing: card.distributeRows ? 0 : card.contentSpacing
        Repeater {
            model: card.rows
            delegate: FieldRow {
                required property var modelData
                caption: modelData.caption
                value: modelData.value
                captionSize: card.captionSize
                valueSize: card.valueSize
                expand: card.distributeRows
                Layout.fillHeight: card.distributeRows
            }
        }
        Item { Layout.fillHeight: !card.distributeRows }
        Text {
            visible: bridge.errorText !== ""
            text: bridge.errorText
            color: Theme.bad
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontCaption
        }
        ConfirmRedoBar {
            visible: card.showActions
            Layout.preferredHeight: visible ? implicitHeight : 0
            Layout.maximumHeight: visible ? 100000 : 0
            onConfirm: card.confirm()
            onRedo: card.redo()
        }
    }
}
