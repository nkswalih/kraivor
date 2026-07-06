const AI_URL = process.env.AI_API_URL ?? 'http://localhost:8004';

export async function POST(
  req: Request,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const path = (await params).path.join('/');
  const body = await req.json();
  const token = req.headers.get('authorization')?.replace('Bearer ', '');

  const response = await fetch(`${AI_URL}/${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });

  const contentType = response.headers.get('content-type') ?? '';

  if (contentType.includes('text/event-stream')) {
    if (!response.body) {
      return new Response(null, { status: 204 });
    }
    return new Response(response.body, {
      status: response.status,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
    });
  }

  const data = await response.json().catch(() => ({}));
  return Response.json(data, { status: response.status });
}

export async function GET(
  req: Request,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const path = (await params).path.join('/');
  const url = new URL(req.url);
  const query = url.search;
  const token = req.headers.get('authorization')?.replace('Bearer ', '');

  const response = await fetch(`${AI_URL}/${path}${query}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  const data = await response.json().catch(() => ({}));
  return Response.json(data, { status: response.status });
}

export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const path = (await params).path.join('/');
  const body = await req.json();
  const token = req.headers.get('authorization')?.replace('Bearer ', '');

  const response = await fetch(`${AI_URL}/${path}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });

  const data = await response.json().catch(() => ({}));
  return Response.json(data, { status: response.status });
}
