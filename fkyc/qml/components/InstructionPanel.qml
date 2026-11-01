import QtQuick
import Fkyc 1.0

Column {
    id: root
    property real unit: 1
    spacing: 16 * unit
    width: 250 * unit

    Text {
        text: "Instructions"
        color: Theme.ink
        font.family: Theme.fontFamily
        font.pixelSize: 28 * root.unit
        font.weight: Font.Bold
        style: Text.Raised
        styleColor: "#33000000"
    }

    Row {
        width: parent.width
        spacing: 10 * root.unit

        Text {
            text: "•"
            color: Theme.ink
            font.family: Theme.fontFamily
            font.pixelSize: 18 * root.unit
            font.weight: Font.Bold
        }
        Text {
            width: parent.width - 24 * root.unit
            text: bridge.errorText !== "" ? bridge.errorText : (bridge.prompt || "")
            color: Theme.ink
            wrapMode: Text.WordWrap
            font.family: Theme.fontFamily
            font.pixelSize: 16 * root.unit
            font.weight: Font.Medium
            style: Text.Raised
            styleColor: "#33000000"
        }
    }
}
