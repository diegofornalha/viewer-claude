'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Eye, Download, FileText, Calendar, FolderOpen } from 'lucide-react'
import { toast } from 'sonner'

interface SessionInfo {
  session_id: string
  directory: string
  full_path: string
  file_path: string
}

interface SessionsList {
  sessions: SessionInfo[]
}

interface SessionStats {
  total_sessions: number
  directories: number
  sessions_by_directory: Record<string, number>
  claude_projects_path: string
}

export default function SessionViewerPage() {
  const [sessions, setSessions] = useState<SessionInfo[]>([])
  const [stats, setStats] = useState<SessionStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedDirectory, setSelectedDirectory] = useState<string>('all')

  useEffect(() => {
    loadSessions()
    loadStats()
  }, [])

  const loadSessions = async () => {
    try {
      const response = await fetch('/api/claude-sessions/')
      if (response.ok) {
        const data: SessionsList = await response.json()
        setSessions(data.sessions)
      } else {
        toast.error('Erro ao carregar sessões')
      }
    } catch (error) {
      toast.error('Erro de conexão com o servidor')
      console.error('Error loading sessions:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadStats = async () => {
    try {
      const response = await fetch('/api/claude-sessions/stats')
      if (response.ok) {
        const data: SessionStats = await response.json()
        setStats(data)
      }
    } catch (error) {
      console.error('Error loading stats:', error)
    }
  }

  const viewSession = async (directory: string, sessionId: string) => {
    try {
      const response = await fetch(`/api/claude-sessions/${directory}/${sessionId}`)
      if (response.ok) {
        const data = await response.json()
        // Por enquanto apenas mostra no console
        console.log('Session data:', data)
        toast.success(`Sessão ${sessionId} carregada (ver console)`)
      } else {
        toast.error('Erro ao carregar sessão')
      }
    } catch (error) {
      toast.error('Erro ao carregar sessão')
    }
  }

  const exportSession = async (directory: string, sessionId: string, format: string = 'json') => {
    try {
      const response = await fetch(`/api/claude-sessions/${directory}/${sessionId}/export?format=${format}`)
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `session-${sessionId}.${format}`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
        toast.success(`Sessão exportada em ${format.toUpperCase()}`)
      } else {
        toast.error('Erro ao exportar sessão')
      }
    } catch (error) {
      toast.error('Erro ao exportar sessão')
    }
  }

  const filteredSessions = selectedDirectory === 'all' 
    ? sessions 
    : sessions.filter(s => s.directory === selectedDirectory)

  const directories = Array.from(new Set(sessions.map(s => s.directory))).sort()

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-lg">Carregando sessões...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <FolderOpen className="h-8 w-8 text-primary" />
          <h1 className="text-3xl font-bold">Claude Session Viewer</h1>
        </div>
        <p className="text-muted-foreground">
          Visualize e explore suas sessões do Claude Code
        </p>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total de Sessões</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_sessions}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Diretórios</CardTitle>
              <FolderOpen className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.directories}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Caminho</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-xs text-muted-foreground truncate">
                {stats.claude_projects_path}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Directory Filter */}
      <div className="mb-6">
        <div className="flex gap-2 flex-wrap">
          <Button
            variant={selectedDirectory === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedDirectory('all')}
          >
            Todos ({sessions.length})
          </Button>
          {directories.map(dir => (
            <Button
              key={dir}
              variant={selectedDirectory === dir ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedDirectory(dir)}
            >
              {dir} ({sessions.filter(s => s.directory === dir).length})
            </Button>
          ))}
        </div>
      </div>

      {/* Sessions List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredSessions.length === 0 ? (
          <div className="col-span-full">
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <FolderOpen className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-2">Nenhuma sessão encontrada</h3>
                <p className="text-sm text-muted-foreground">
                  Não há sessões disponíveis no diretório selecionado
                </p>
              </CardContent>
            </Card>
          </div>
        ) : (
          filteredSessions.map((session) => (
            <Card key={`${session.directory}-${session.session_id}`} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <CardTitle className="text-lg truncate">{session.session_id}</CardTitle>
                <CardDescription>
                  <div className="flex items-center gap-1">
                    <FolderOpen className="h-3 w-3" />
                    {session.directory}
                  </div>
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => viewSession(session.directory, session.session_id)}
                  >
                    <Eye className="h-3 w-3 mr-1" />
                    Ver
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => exportSession(session.directory, session.session_id, 'json')}
                  >
                    <Download className="h-3 w-3 mr-1" />
                    JSON
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => exportSession(session.directory, session.session_id, 'markdown')}
                  >
                    <FileText className="h-3 w-3 mr-1" />
                    MD
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="mt-12 text-center text-sm text-muted-foreground">
        <p>Claude Session Viewer - Visualização de sessões do Claude Code</p>
      </div>
    </div>
  )
}