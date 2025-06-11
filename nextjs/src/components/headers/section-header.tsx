interface Props {
    type: "inline" | "default"
    head: string
    text: string
}

export const SectionHeader: React.FC<Props> = ({ type, head, text }) => {
  return (
    <div className={type === "inline" ? "headSectionInline__wrapper" : "headSection__wrapper"}>
    <h2>{head}</h2>
        {text}
    </div>
  )
}
