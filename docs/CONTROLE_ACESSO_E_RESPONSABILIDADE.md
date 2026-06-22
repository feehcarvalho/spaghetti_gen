# Controle de Acesso e Responsabilidade SPS

## Objetivo

A tela inicial controla o acesso local a aplicacao e registra que o usuario leu e aceitou a responsabilidade tecnica antes de usar a IA SPS.

A IA apoia a criacao, revisao e melhoria de padroes operacionais, mas nao aprova padrao automaticamente.

## Cadastro de logins autorizados

Os logins ficam em:

```text
data/security/authorized_logins.csv
```

Formato:

```csv
login,nome,area,perfil,ativo
m123456,Nome Sobrenome,Engenharia de Processos,user,true
admin,Administrador Local,Engenharia,admin,true
```

O campo `login` e obrigatorio. O campo `ativo=true` libera acesso. Para bloquear ou remover um usuario, altere `ativo` para `false` ou remova a linha.

A comparacao ignora maiusculas/minusculas, espacos antes/depois e aceita e-mail usando apenas a parte antes do `@`.

## Aceite de responsabilidade

Antes de acessar a ferramenta, o usuario deve marcar:

```text
Li, compreendi e assumo a responsabilidade de revisar tecnicamente a analise antes de utilizar ou autorizar o padrao.
```

Sem aceite, a interface principal nao e exibida.

## Logs de auditoria

Eventos locais de acesso ficam em:

```text
data/audit/login_events.csv
```

Eventos registrados:

- `authorized`
- `denied`
- `accepted_responsibility`
- `logout`

O log nao salva chave de API, documentos, videos ou conteudo da analise.

## Limitacao

Este controle usa login local sem senha. Ele nao substitui autenticacao corporativa robusta.

Recomendacao futura: integrar SSO, Active Directory ou Microsoft Entra ID.

## Regras de uso responsavel

- A IA apoia, nao aprova.
- Validacao no gemba e obrigatoria.
- Lideranca e SPS devem revisar quando aplicavel.
- Quem autoriza o padrao assume responsabilidade tecnica.
- Preservar cultura SPS, seguranca, qualidade, ergonomia e estabilidade do metodo.
