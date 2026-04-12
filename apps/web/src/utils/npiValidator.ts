export function isValidNpi(value: string): boolean {
  if (!/^\d{10}$/.test(value)) {
    return false
  }

  const digits = `80840${value}`
    .split('')
    .map((char) => Number(char))
    .reverse()

  const checksum = digits.reduce((sum, digit, index) => {
    if (index % 2 === 1) {
      const doubled = digit * 2
      return sum + Math.floor(doubled / 10) + (doubled % 10)
    }

    return sum + digit
  }, 0)

  return checksum % 10 === 0
}
