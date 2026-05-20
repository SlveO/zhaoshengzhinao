interface ModalProps {
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  onConfirm: () => void
  onCancel: () => void
}

export default function Modal({ open, title, message, confirmLabel = '删除', onConfirm, onCancel }: ModalProps) {
  if (!open) return null

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{title}</h3>
        <p>{message}</p>
        <div className="btn-group" style={{ justifyContent: 'flex-end' }}>
          <button className="btn btn-secondary" onClick={onCancel}>取消</button>
          <button className="btn btn-danger" onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  )
}
