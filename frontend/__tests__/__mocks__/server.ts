/**
 * MSW Server Setup
 * Shared test server for all frontend tests
 */
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

export const server = setupServer(...handlers)
