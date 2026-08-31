import { useState } from 'react'

export default function usePagination(initial = { page: 1, pageSize: 20 }) {
  const [page, setPage] = useState(initial.page)
  const [pageSize, setPageSize] = useState(initial.pageSize)
  return { page, pageSize, setPage, setPageSize }
}
