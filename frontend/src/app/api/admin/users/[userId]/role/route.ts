import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ userId: string }> }
) {
  try {
    const { userId } = await params
    
    // Get the authorization header from the request
    const authHeader = request.headers.get('authorization')
    
    if (!authHeader) {
      return NextResponse.json(
        { error: 'Authorization header required' },
        { status: 401 }
      )
    }
    
    // Get the role from request body
    const { role } = await request.json()
    
    if (!role || !['free', 'premium', 'admin'].includes(role)) {
      return NextResponse.json(
        { error: 'Invalid role. Must be free, premium, or admin' },
        { status: 400 }
      )
    }
    
    const headers: Record<string, string> = {
      'Authorization': authHeader,
      'Content-Type': 'application/json',
    }
    
    const response = await fetch(`${BACKEND_URL}/admin/users/${userId}/role`, {
      method: 'PUT',
      headers,
      body: JSON.stringify({ role })
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