import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    // Get the authorization header from the request
    const authHeader = request.headers.get('authorization')
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    
    // Add authorization header if present
    if (authHeader) {
      headers['Authorization'] = authHeader
    }
    
    const response = await fetch(`${BACKEND_URL}/generate`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      // Try to parse as JSON first, fallback to text
      let errorData
      try {
        errorData = await response.json()
      } catch {
        const errorText = await response.text()
        errorData = { error: errorText }
      }
      
      return NextResponse.json(errorData, { status: response.status })
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