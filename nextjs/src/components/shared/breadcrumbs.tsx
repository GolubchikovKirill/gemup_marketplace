import Link from "next/link";

interface Props {
    initial?: string
    name: string
}

export const Breadcrumbs: React.FC<Props> = ({
    initial = "Home",
    name = ""
}) => {
  return (
    <div className="breadcrumbs">
      <div className="breadcrumbs-wrapper container">
        <ol itemScope itemType="http://schema.org/BreadcrumbList">
          <li
            itemProp="itemListElement"
            itemScope
            itemType="http://schema.org/ListItem"
          >
            <Link itemProp="item" href="/">
              <span className="name" itemProp="name">
                {initial}
              </span>
              <i className="ico-arrow"></i>
            </Link>
            <meta itemProp="position" content="1" />
          </li>
          <li
            itemProp="itemListElement"
            itemScope
            itemType="http://schema.org/ListItem"
          >
            <span className="active">{name}</span>
            <meta itemProp="position" content="2" />
          </li>
        </ol>
      </div>
    </div>
  );
};
