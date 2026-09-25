import { PGlite } from '@electric-sql/pglite';
import { PGLiteSocketServer } from '@electric-sql/pglite-socket';
const db = await PGlite.create(process.env.PGLITE_DATA || './.pgdata');
const server = new PGLiteSocketServer({ db, host: '127.0.0.1', port: Number(process.env.PGPORT || 5432) });
await server.start();
process.stdout.write('Portable PostgreSQL listening on 127.0.0.1:5432\n');
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, async () => { await server.stop(); await db.close(); process.exit(0); });
