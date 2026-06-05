import { useRef, useState } from 'react'

interface FileUploadProps {
  onUploaded: (info: { id: string; original_filename: string; file_size: number; mime_type: string | null }) => void
  onUploadStart?: (file: File) => Promise<{ id: string; original_filename: string; file_size: number; mime_type: string | null }>
  accept?: string
}

export default function FileUpload({ onUploaded, onUploadStart, accept = '.pdf,.docx,.xlsx,.pptx,.doc,.xls,.ppt,.jpg,.jpeg,.png,.gif,.zip,.txt' }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [fileName, setFileName] = useState('')
  const [error, setError] = useState('')

  const handleFile = async (file: File) => {
    setError('')
    setFileName(file.name)
    setUploading(true)
    setProgress(0)

    try {
      if (onUploadStart) {
        const result = await onUploadStart(file)
        onUploaded(result)
      } else {
        // Fallback: create a mock file entry for demo mode
        setTimeout(() => {
          setProgress(100)
          onUploaded({
            id: 'f-' + Date.now(),
            original_filename: file.name,
            file_size: file.size,
            mime_type: file.type || null,
          })
          setUploading(false)
        }, 800)
        return
      }
      setUploading(false)
    } catch (e: any) {
      setError(e?.message || '上传失败')
      setUploading(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files?.[0]
    if (file) handleFile(file)
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  return (
    <div>
      <div
        className="upload-zone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        style={{ cursor: 'pointer' }}
      >
        {uploading ? (
          <div className="upload-progress-wrap">
            <span style={{ fontSize: 13, marginBottom: 6, display: 'block' }}>{fileName}</span>
            <div className="upload-progress">
              <div className="upload-progress-bar" style={{ width: `${progress}%` }} />
            </div>
            <span style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 4, display: 'block' }}>{progress}%</span>
          </div>
        ) : (
          <div style={{ textAlign: 'center' }}>
            <span style={{ fontSize: 24, opacity: 0.3, display: 'block', marginBottom: 6 }}>📁</span>
            <span style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>拖拽文件到此处，或点击选择文件</span>
            <span style={{ fontSize: 11, color: 'var(--color-text-muted)', display: 'block', marginTop: 4 }}>
              支持 PDF、Word、Excel、PPT、图片、ZIP，最大 20MB
            </span>
          </div>
        )}
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          style={{ display: 'none' }}
          onChange={handleChange}
        />
      </div>
      {error && (
        <div style={{ fontSize: 12, color: 'var(--color-danger)', marginTop: 6 }}>{error}</div>
      )}
    </div>
  )
}
