import QtQuick
import QtQuick.Layouts
import Fkyc 1.0

ColumnLayout {
    property string caption: ""
    property string value: ""
    property real captionSize: 0
    property real valueSize: 0
    property color captionColor: Theme.muted
    property color valueColor: Theme.inkOnLight
    property int maxLines: 1
    property int captionWeight: Font.Medium
    property bool expand: false
    spacing: expand ? 6 : 2
    Layout.fillWidth: true

    Item {
        visible: expand
        Layout.fillHeight: true
        Layout.preferredHeight: expand ? 1 : 0
        Layout.maximumHeight: expand ? 100000 : 0
    }
    Text {
        text: caption
        color: captionColor
        font.family: Theme.fontFamily
        font.pixelSize: captionSize > 0 ? captionSize : Theme.fontCaption
        font.weight: captionWeight
    }
    Text {
        text: value === "" ? "—" : value
        color: valueColor
        font.family: Theme.fontFamily
        font.pixelSize: valueSize > 0 ? valueSize : Theme.fontBody
        font.weight: Font.Bold
        Layout.fillWidth: true
        elide: Text.ElideNone
        wrapMode: Text.NoWrap
        maximumLineCount: Math.max(1, maxLines)
        fontSizeMode: Text.HorizontalFit
        minimumPixelSize: 16
    }
    Item {
        visible: expand
        Layout.fillHeight: true
        Layout.preferredHeight: expand ? 1 : 0
        Layout.maximumHeight: expand ? 100000 : 0
    }
}
