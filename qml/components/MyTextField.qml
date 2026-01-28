import Lomiri.Components 1.3 as UITK
import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12

Item {
    property string title
    property alias text: tf.text
    property string placeholder: ''
    property alias enabled: tf.enabled
    property alias control: controlContainer.children
    signal changed(string text)

    anchors.left: parent.left
    anchors.right: parent.right
    anchors.leftMargin: units.gu(2)
    anchors.rightMargin: units.gu(2)

    height: childrenRect.height

    ColumnLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: units.gu(1)

        UITK.TextField {
            id: tf
            Layout.fillWidth: true
            placeholderText: '<font color="' + theme.palette.normal.backgroundTertiaryText + '">' + placeholder + '</font>'
            onTextChanged: changed(text)
        }

        Item {
            id: controlContainer
            Layout.fillWidth: true
            implicitHeight: childrenRect.height
        }
    }

    Label {
        id: lb
        x: tf.x + units.gu(1.5)
        y: tf.y - height / 2
        z: 2
        text: title
        color: theme.palette.normal.foregroundText
        font.pixelSize: units.gu(1.25)
    }

    Rectangle {
        color: tf.enabled ? theme.palette.normal.background : '#ddd'
        x: lb.x - units.gu(0.5)
        y: tf.y
        width: lb.width + units.gu(1)
        height: lb.height / 2
    }
}