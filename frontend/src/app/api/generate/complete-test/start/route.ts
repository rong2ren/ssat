import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    let body
    try {
      body = await request.json()
    } catch {
      // Handle aborted/malformed requests gracefully
      return NextResponse.json(
        { error: 'Invalid JSON in request body' },
        { status: 400 }
      )
    }
    
    if (!body || Object.keys(body).length === 0) {
      return NextResponse.json(
        { error: 'Request body is empty' },
        { status: 400 }
      )
    }
    
    const response = await fetch(`${BACKEND_URL}/generate/complete-test/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const errorText = await response.text()
      return NextResponse.json(
        { error: `Backend error: ${response.status} - ${errorText}` },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('API proxy error:', error)
    return NextResponse.json(
      { error: 'Failed to connect to backend' },
      { status: 500 }
    )
  }
}