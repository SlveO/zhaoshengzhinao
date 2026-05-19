import { useEffect, useState } from 'react'
import api from '../api/client'
import type { DocumentItem } from '../types'
import StatusCard from '../components/StatusCard'
import PageHeader from '../components/PageHeader'

export default function KnowledgeSettingsPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<{ documents: DocumentItem[] }>('/admin/knowledge/documents')
      .then((r) => setDocs(r.data.documents))
      .catch((e) => setError(e?.message || '获取知识库文档失败'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="知识库管理"
        subtitle="管理院校专属知识库文档，数据将用于 AI 对话检索"
        extra={
          <button
            disabled
            className="px-4 py-2 rounded-lg text-white font-medium text-sm transition cursor-not-allowed opacity-50"
            style={{ background: 'var(--brand-primary)' }}
          >
            上传文档
          </button>
        }
      />

      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <StatusCard
          loading={loading}
          error={error}
          empty={!loading && !error && docs.length === 0}
          emptyHint="上传 Excel 或文档文件来构建知识库"
        >
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="text-left px-6 py-3 font-medium text-gray-600">文档名称</th>
                <th className="text-left px-6 py-3 font-medium text-gray-600">类型</th>
                <th className="text-left px-6 py-3 font-medium text-gray-600">年份</th>
                <th className="text-left px-6 py-3 font-medium text-gray-600">索引状态</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((doc) => (
                <tr key={doc.id} className="border-b last:border-0 hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-3 text-gray-800">{doc.title}</td>
                  <td className="px-6 py-3 text-gray-500">{doc.data_type}</td>
                  <td className="px-6 py-3 text-gray-500">{doc.year || '-'}</td>
                  <td className="px-6 py-3">
                    {doc.indexed_at ? (
                      <span className="text-green-600 text-xs bg-green-50 px-2 py-0.5 rounded-full">
                        已索引
                      </span>
                    ) : (
                      <span className="text-amber-600 text-xs bg-amber-50 px-2 py-0.5 rounded-full">
                        未索引
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </StatusCard>
      </div>
    </div>
  )
}
