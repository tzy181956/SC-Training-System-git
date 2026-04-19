import axios from 'axios'

const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL ||
  `${window.location.protocol}//${window.location.hostname}:8000/api`

const client = axios.create({
  baseURL: apiBaseUrl,
})

export default client
