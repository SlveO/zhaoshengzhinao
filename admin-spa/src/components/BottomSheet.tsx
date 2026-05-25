import { useEffect, type ReactNode } from 'react'

interface BottomSheetProps {
  open: boolean
  title?: string
  onClose: () => void
  children: ReactNode
}

export default function BottomSheet({ open, title, onClose, children }: BottomSheetProps) {
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => { document.body.style.overflow = '' }
  }, [open])

  if (!open) return null

  return (
    <>
      <div
        className="bs-overlay"
        onClick={onClose}
      />
      <div className="bs-panel">
        <div className="bs-handle" />
        {title && <div className="bs-title">{title}</div>}
        {children}
      </div>
    </>
  )
}
