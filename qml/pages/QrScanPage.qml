import QtQuick 2.12
import QtQuick.Layouts 1.12
import QtMultimedia 5.12
import Lomiri.Components 1.3 as UITK
import io.thp.pyotherside 1.3

UITK.Page {
    id: qrPage
    signal qrDecoded(string text)

    property bool scanning: true
    property bool decoding: false
    property string capturePath: "/tmp/wg_qr_capture.jpg"

    header: UITK.PageHeader {
        title: i18n.tr("Сканировать QR-код")
        trailingActionBar.actions: [
            UITK.Action {
                iconName: "close"
                onTriggered: {
                    scanning = false
                    captureTimer.stop()
                    camera.stop()
                    pageStack.pop()
                }
            }
        ]
    }

    Camera {
        id: camera
        captureMode: Camera.CaptureStillImage
        onCameraStatusChanged: {
            if (cameraStatus === Camera.ActiveStatus && !captureTimer.running) {
                captureTimer.start()
            }
        }
    }

    ImageCapture {
        id: imageCapture
        camera: camera
        onImageSaved: function(id, path) {
            if (!scanning) return
            decodeImage(path)
        }
        onError: {
            decoding = false
            statusText.text = i18n.tr("Ошибка камеры")
        }
    }

    VideoOutput {
        anchors.fill: parent
        anchors.topMargin: header.height
        source: camera
        autoOrientation: true
        fillMode: VideoOutput.PreserveAspectCrop
    }

    Rectangle {
        id: scanFrame
        width: parent.width * 0.62
        height: width
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        color: "transparent"
        border.width: units.gu(0.3)
        border.color: "white"
        radius: units.gu(1)
    }

    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: units.gu(3)
        spacing: units.gu(0.6)

        Text {
            id: statusText
            text: i18n.tr("Наведите камеру на QR-код")
            color: "white"
            font.pixelSize: units.gu(1.7)
            horizontalAlignment: Text.AlignHCenter
        }

        UITK.ActivityIndicator {
            running: decoding
            visible: decoding
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }

    Timer {
        id: captureTimer
        interval: 900
        repeat: true
        running: scanning && camera.cameraStatus === Camera.ActiveStatus && !decoding
        onTriggered: {
            decoding = true
            imageCapture.captureToLocation(capturePath)
        }
    }

    function decodeImage(path) {
        var cleanPath = path
        if (cleanPath.startsWith("file://")) {
            cleanPath = cleanPath.substring(7)
        }
        python.call('vpn.instance.decode_qr_image', [cleanPath], function(result) {
            if (result.error) {
                if (result.error === "NO_QR") {
                    decoding = false
                    return
                }
                decoding = false
                statusText.text = i18n.tr("Не удалось распознать QR")
                toast.show(i18n.tr("QR error: ") + result.error)
                return
            }
            decoding = false
            scanning = false
            captureTimer.stop()
            camera.stop()
            qrPage.qrDecoded(result.text)
            pageStack.pop()
        })
    }

    Component.onCompleted: {
        camera.start()
    }

    Component.onDestruction: {
        scanning = false
        captureTimer.stop()
        camera.stop()
    }
}
