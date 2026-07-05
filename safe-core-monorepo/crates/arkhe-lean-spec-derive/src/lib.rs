extern crate proc_macro;
use proc_macro::TokenStream;
use quote::quote;
use syn::{parse_macro_input, DeriveInput, Data, Fields, Type};

#[proc_macro_derive(LeanSpec)]
pub fn lean_spec_derive(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input as DeriveInput);
    let name = &input.ident;

    let fields = match &input.data {
        Data::Struct(data) => match &data.fields {
            Fields::Named(f) => &f.named,
            _ => panic!("LeanSpec: apenas structs com campos nomeados"),
        },
        _ => panic!("LeanSpec: apenas structs"),
    };

    let lean_code = generate_lean(name, fields);

    TokenStream::from(quote! {
        impl #name {
            pub fn to_lean_spec(&self) -> String { #lean_code.to_string() }
            pub fn to_lean_theorem(&self, property: &str) -> String {
                format!("theorem {}_{} : {} := by sorry", stringify!(#name), property, property)
            }
        }
    })
}

fn generate_lean(name: &syn::Ident, fields: &syn::punctuated::Punctuated<syn::Field, syn::Token![,]>) -> String {
    let defs: Vec<String> = fields.iter().map(|f| {
        format!("  {} : {}", f.ident.as_ref().unwrap(), type_to_lean(&f.ty))
    }).collect();
    format!("/-- Lean 4 spec for {}\nstructure {} where\n{}\n", name, name, defs.join("\n"))
}

fn type_to_lean(ty: &Type) -> String {
    match ty {
        Type::Path(p) => {
            let s = p.path.segments.last().unwrap().ident.to_string();
            match s.as_str() {
                "usize" | "u64" | "u32" | "u16" | "u8" => "Nat",
                "i64" | "i32" | "i16" | "i8" | "isize" => "Int",
                "bool" => "Bool", "String" => "String", _ => &s,
            }.to_string()
        }
        _ => "Type".to_string(),
    }
}
