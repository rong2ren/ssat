import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    // Forward the request to the backend
    const response = await fetch(`${BACKEND_URL}/admin/migration-statistics`, {
      method: 'GET',
      headers: {
        'Authorization': request.headers.get('Authorization') || '',
      },
    })

    const data = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { error: data.detail || 'Failed to get migration statistics' },
        { status: response.status }
      )
    }

    return NextResponse.json(data)
  } catch (error) {
    console.error('Migration statistics proxy error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
} 