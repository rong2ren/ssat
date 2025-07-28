import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params
  const pathStr = path.join('/')
  const url = new URL(request.url)
  
  console.log(`🔍 Frontend API: GET /auth/${pathStr} - ${new Date().toISOString()}`)
  
  try {
    const response = await fetch(`${BACKEND_URL}/auth/${pathStr}${url.search}`, {
      method: 'GET',
      headers: {
        'Authorization': request.headers.get('Authorization') || '',
        'Content-Type': 'application/json',
      },
    })

    const data = await response.json()
    
    if (!response.ok) {
      console.error(`❌ Frontend API Error: GET /auth/${pathStr} - Status: ${response.status}`)
      console.error(`❌ Error Details:`, data)
    }
    
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error(`❌ Frontend API Exception: GET /auth/${pathStr}`)
    console.error(`❌ Exception Details:`, error)
    return NextResponse.json(
      { success: false, message: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params
  const pathStr = path.join('/')
  const body = await request.json()
  
  console.log(`🔍 Frontend API: POST /auth/${pathStr} - ${new Date().toISOString()}`)
  console.log(`🔍 Request Body:`, body)
  
  try {
    const response = await fetch(`${BACKEND_URL}/auth/${pathStr}`, {
      method: 'POST',
      headers: {
        'Authorization': request.headers.get('Authorization') || '',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    const data = await response.json()
    
    if (!response.ok) {
      console.error(`❌ Frontend API Error: POST /auth/${pathStr} - Status: ${response.status}`)
      console.error(`❌ Error Details:`, data)
    }
    
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error(`❌ Frontend API Exception: POST /auth/${pathStr}`)
    console.error(`❌ Exception Details:`, error)
    return NextResponse.json(
      { success: false, message: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params
  const pathStr = path.join('/')
  const body = await request.json()
  
  console.log(`🔍 Frontend API: PUT /auth/${pathStr} - ${new Date().toISOString()}`)
  console.log(`🔍 Request Body:`, body)
  
  try {
    const response = await fetch(`${BACKEND_URL}/auth/${pathStr}`, {
      method: 'PUT',
      headers: {
        'Authorization': request.headers.get('Authorization') || '',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    const data = await response.json()
    
    if (!response.ok) {
      console.error(`❌ Frontend API Error: PUT /auth/${pathStr} - Status: ${response.status}`)
      console.error(`❌ Error Details:`, data)
    }
    
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error(`❌ Frontend API Exception: PUT /auth/${pathStr}`)
    console.error(`❌ Exception Details:`, error)
    return NextResponse.json(
      { success: false, message: 'Internal server error' },
      { status: 500 }
    )
  }
} 