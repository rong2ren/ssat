import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    // Get the authorization header from the request
    const authHeader = request.headers.get('authorization')
    
    if (!authHeader) {
      return NextResponse.json(
        { error: 'Authorization header required' },
        { status: 401 }
      )
    }
    
    // Get section and difficulty parameters from URL
    const { searchParams } = new URL(request.url)
    const section = searchParams.get('section')
    const difficulty = searchParams.get('difficulty')
    
    console.log('🔍 API ROUTE: Received parameters:', { section, difficulty })
    
    const headers: Record<string, string> = {
      'Authorization': authHeader,
      'Content-Type': 'application/json',
    }
    
    // Build URL with parameters
    const urlParams = new URLSearchParams()
    if (section) urlParams.append('section', section)
    if (difficulty) urlParams.append('difficulty', difficulty)
    
    const url = `${BACKEND_URL}/admin/training-examples${urlParams.toString() ? '?' + urlParams.toString() : ''}`
    
    const response = await fetch(url, {
      method: 'GET',
      headers,
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
