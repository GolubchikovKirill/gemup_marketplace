interface Props {
    name: string
}

export const PageHeader: React.FC<Props> = ({ name }) => {
  return (
    <div className="page__header container">
        <h1>{name}</h1>
    </div>
  )
}