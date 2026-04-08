import { useEffect, useRef } from 'react'
import { Niivue } from '@niivue/niivue'

/**
 * NiiVue-based viewer for NIfTI volumes and overlay masks.
 *
 * Props:
 *   volumeUrl  - URL of the base NIfTI volume
 *   overlayUrl - (optional) URL of a NIfTI mask to overlay
 */
export default function NiiVueViewer({ volumeUrl, overlayUrl }) {
  const canvasRef = useRef(null)
  const nvRef = useRef(null)

  useEffect(() => {
    if (!canvasRef.current || !volumeUrl) return

    const nv = new Niivue({ show3Dcrosshair: true })
    nvRef.current = nv
    nv.attachToCanvas(canvasRef.current)

    const volumes = [{ url: volumeUrl, colormap: 'gray', opacity: 1 }]
    if (overlayUrl) {
      volumes.push({ url: overlayUrl, colormap: 'warm', opacity: 0.5 })
    }

    nv.loadVolumes(volumes)

    return () => {
      nv.closeDrawing()
    }
  }, [volumeUrl, overlayUrl])

  if (!volumeUrl) {
    return <p style={{ color: '#888', fontStyle: 'italic' }}>No volume selected.</p>
  }

  return (
    <canvas
      ref={canvasRef}
      style={{ width: '100%', height: 400, borderRadius: 4, background: '#000' }}
    />
  )
}
