
### Substrato 319.1 - Caster Software
A integração atual de `wireguard-go` no Linux é realizada via chamadas FFI ou processos filhos (sidecar) para manipular FDs TUN. **Isso é uma violação do Princípio de Superfície de Ataque Mínima**.
O runtime do Go expande a superfície de ataque, impossibilita `no_std` pleno nos builds de borda e dificulta auditorias de segurança formais.

**Resolução Canônica:**
Para produção nativa no ARKHE, devemos substituir a integração do `wireguard-go` pelo **`boringtun`** (escrito em Rust pela Cloudflare). Isso permitirá um túnel completamente no mesmo espaço de memória, sem syscalls inseguras como `fork()` ou a imprevisibilidade do garbage collector do Go.
